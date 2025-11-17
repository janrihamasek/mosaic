"""
Entries service.

Handles entry listing, upserts, deletions, and day finalization with cache
coordination delegated to appropriate helpers.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from audit import log_event
from repositories import entries_repo
from security import ValidationError, validate_entry_payload, validate_finalize_day_payload
from .common import db_transaction
from .idempotency import lookup as idempotency_lookup, store_response as idempotency_store_response


def list_entries(
    *,
    user_id: int,
    is_admin: bool,
    start_date: Optional[str],
    end_date: Optional[str],
    activity_filter: Optional[str],
    category_filter: Optional[str],
    limit: int,
    offset: int,
) -> List[Dict[str, Any]]:
    # validate dates
    try:
        if start_date:
            datetime.strptime(start_date, "%Y-%m-%d")
        if end_date:
            datetime.strptime(end_date, "%Y-%m-%d")
    except ValueError:
        raise ValidationError("Invalid date filter", code="invalid_query", status=400)

    try:
        return entries_repo.list_entries(
            user_id,
            is_admin,
            start_date,
            end_date,
            activity_filter,
            category_filter,
            limit,
            offset,
        )
    except SQLAlchemyError as exc:
        raise ValidationError(str(exc), code="database_error", status=500)


def add_entry(
    *,
    user_id: int,
    payload: Dict[str, Any],
    idempotency_key: Optional[str],
    invalidate_cache_cb=None,
) -> Tuple[Dict[str, Any], int]:
    data = validate_entry_payload(payload or {})
    date = data["date"]
    activity = data["activity"]
    note = data["note"]
    float_value = data["value"]

    cached = idempotency_lookup(user_id, idempotency_key)
    if cached:
        return cached

    try:
        with db_transaction():
            activity_row = entries_repo.get_activity_metadata(activity, user_id)

            description = activity_row["description"] if activity_row else ""
            activity_category = activity_row["category"] if activity_row else ""
            activity_goal = activity_row["goal"] if activity_row else 0
            activity_type_value = (activity_row["activity_type"] if activity_row else None) or "positive"

            existing_entry = entries_repo.get_existing_entry(date, activity, user_id)
            if not activity_row and existing_entry:
                activity_category = existing_entry["activity_category"] or activity_category
                activity_goal = (
                    existing_entry["activity_goal"] if existing_entry["activity_goal"] is not None else activity_goal
                )
                activity_type_value = existing_entry["activity_type"] or activity_type_value
            if not activity_row:
                try:
                    entries_repo.create_activity_for_entry(
                        activity,
                        activity_category or "",
                        float(activity_goal or 0),
                        description or "",
                        user_id,
                    )
                except IntegrityError:
                    pass

            updates = {
                "value": float_value,
                "note": note,
                "description": description,
                "activity_category": activity_category,
                "activity_goal": activity_goal,
                "activity_type": activity_type_value,
                "user_id": user_id,
            }

            rowcount = entries_repo.update_entry_by_date_and_activity(date, activity, user_id, updates)

            if rowcount > 0:
                response_payload = {"message": "Záznam aktualizován"}
                status_code = 200
            else:
                rowcount = entries_repo.update_entry_by_date_and_activity(date, activity, None, updates)

                if rowcount > 0:
                    response_payload = {"message": "Záznam aktualizován"}
                    status_code = 200
                else:
                    entries_repo.create_entry(
                        date,
                        activity,
                        float_value,
                        note,
                        description,
                        activity_category,
                        activity_goal,
                        activity_type_value,
                        user_id,
                    )
                    response_payload = {"message": "Záznam uložen"}
                    status_code = 201
    except SQLAlchemyError as exc:
        raise ValidationError(str(exc), code="database_error", status=500)

    if invalidate_cache_cb:
        invalidate_cache_cb("today")
        invalidate_cache_cb("stats")
    idempotency_store_response(user_id, idempotency_key, response_payload, status_code)
    return response_payload, status_code


def delete_entry(
    entry_id: int,
    *,
    user_id: int,
    is_admin: bool,
    invalidate_cache_cb=None,
) -> Tuple[Dict[str, str], int]:
    try:
        rowcount = entries_repo.delete_entry_by_id(entry_id, user_id, is_admin)
        if rowcount == 0:
            log_event(
                "entry.delete_missing",
                "Entry delete attempted but not found",
                user_id=user_id,
                level="warning",
                context={"entry_id": entry_id, "as_admin": is_admin},
            )
            raise ValidationError("Záznam nenalezen", code="not_found", status=404)
    except SQLAlchemyError as exc:
        raise ValidationError(str(exc), code="database_error", status=500)

    if invalidate_cache_cb:
        invalidate_cache_cb("today")
        invalidate_cache_cb("stats")
    log_event(
        "entry.delete",
        "Entry deleted",
        user_id=user_id,
        context={"entry_id": entry_id, "as_admin": is_admin},
    )
    return {"message": "Záznam smazán"}, 200


def finalize_day(
    *,
    user_id: int,
    is_admin: bool,
    payload: Dict[str, Any],
    invalidate_cache_cb=None,
) -> Tuple[Dict[str, str], int]:
    data = validate_finalize_day_payload(payload or {})
    date = data["date"]

    with db_transaction():
        active_activities = entries_repo.get_active_activities_for_date(date, user_id, is_admin)
        existing = entries_repo.get_existing_activities_for_date(date, user_id, is_admin)
        existing_names = {e["activity"] for e in existing}

        new_entries: List[Dict[str, Any]] = []
        for a in active_activities:
            if a["name"] not in existing_names:
                activity_type_value = (a.get("activity_type") or "positive") if isinstance(a, dict) else "positive"
                new_entries.append(
                    {
                        "date": date,
                        "activity": a["name"],
                        "description": a["description"],
                        "value": 0,
                        "note": "",
                        "activity_category": a["category"],
                        "activity_goal": a["goal"],
                        "activity_type": activity_type_value,
                        "user_id": user_id,
                    }
                )

        created = entries_repo.bulk_create_entries(new_entries) if new_entries else 0
    if invalidate_cache_cb:
        invalidate_cache_cb("today")
        invalidate_cache_cb("stats")
    return {"message": f"{created} missing entries added for {date}"}, 200
