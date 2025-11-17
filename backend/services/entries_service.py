"""
Entries service.

Handles entry listing, upserts, deletions, and day finalization with cache
coordination delegated to appropriate helpers.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from audit import log_event
from repositories import entries_repo
from security import (
    ValidationError,
    validate_entry_payload,
    validate_finalize_day_payload,
)
from sqlalchemy.exc import SQLAlchemyError

from .idempotency import lookup as idempotency_lookup
from .idempotency import store_response as idempotency_store_response


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
        status, rowcount = entries_repo.upsert_entry(
            date, activity, float_value, note, user_id
        )
    except SQLAlchemyError as exc:
        raise ValidationError(str(exc), code="database_error", status=500)

    if status == "updated":
        response_payload = {"message": "Záznam aktualizován"}
        status_code = 200
    else:
        response_payload = {"message": "Záznam uložen"}
        status_code = 201

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

    try:
        created = entries_repo.create_missing_entries_for_day(date, user_id, is_admin)
    except SQLAlchemyError as exc:
        raise ValidationError(str(exc), code="database_error", status=500)
    if invalidate_cache_cb:
        invalidate_cache_cb("today")
        invalidate_cache_cb("stats")
    return {"message": f"{created} missing entries added for {date}"}, 200
