"""
Activities service.

Houses activity creation, updates, activation/deactivation, deletion, and
propagation logic. Keep HTTP and Flask concerns out of this layer.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from audit import log_event
from repositories import activities_repo
from security import ValidationError, validate_activity_create_payload, validate_activity_update_payload
from .common import db_transaction
from .idempotency import lookup as idempotency_lookup, store_response as idempotency_store_response


def list_activities(
    *,
    user_id: Optional[int],
    is_admin: bool,
    show_all: bool,
    limit: int,
    offset: int,
) -> List[Dict[str, Any]]:
    try:
        payload = activities_repo.list_activities(user_id, is_admin, show_all, limit, offset)
        return payload
    except SQLAlchemyError as exc:
        raise ValidationError(str(exc), code="database_error", status=500)


def add_activity(
    *,
    user_id: int,
    payload: Dict[str, Any],
    overwrite_existing: bool,
    idempotency_key: Optional[str],
    invalidate_cache_cb=None,
) -> Tuple[Dict[str, Any], int]:
    validated = validate_activity_create_payload(payload or {})
    name = validated["name"]
    category = validated["category"]
    activity_type = validated["activity_type"]
    goal = validated["goal"]
    description = validated["description"]
    frequency_per_day = validated["frequency_per_day"]
    frequency_per_week = validated["frequency_per_week"]

    cached = idempotency_lookup(user_id, idempotency_key)
    if cached:
        payload, status_code = cached
        return payload, status_code

    try:
        activities_repo.create_activity(
            name,
            category,
            activity_type,
            goal,
            description,
            frequency_per_day,
            frequency_per_week,
            user_id,
        )
        response_payload = {"message": "Kategorie přidána"}
        status_code = 201
    except IntegrityError:
        if not overwrite_existing:
            log_event(
                "activity.create_failed",
                "Activity already exists",
                user_id=user_id,
                level="warning",
                context={"name": name},
            )
            raise ValidationError("Aktivita již existuje", code="conflict", status=409)
        try:
            activities_repo.overwrite_activity(
                name,
                category,
                activity_type,
                goal,
                description,
                frequency_per_day,
                frequency_per_week,
                user_id,
            )
        except SQLAlchemyError as exc:
            raise ValidationError(str(exc), code="database_error", status=500)
        else:
            response_payload = {"message": "Aktivita obnovena"}
            status_code = 200
    except SQLAlchemyError as exc:
        raise ValidationError(str(exc), code="database_error", status=500)

    if invalidate_cache_cb:
        invalidate_cache_cb("today")
        invalidate_cache_cb("stats")

    idempotency_store_response(user_id, idempotency_key, response_payload, status_code)
    log_event(
        "activity.create",
        "Activity created",
        user_id=user_id,
        context={"name": name, "category": category},
    )
    return response_payload, status_code


def update_activity(
    activity_id: int,
    *,
    user_id: Optional[int],
    is_admin: bool,
    payload: Dict[str, Any],
    invalidate_cache_cb=None,
) -> Tuple[Dict[str, Any], int]:
    validated = validate_activity_update_payload(payload or {})

    with db_transaction():
        row = activities_repo.get_activity_by_id(activity_id, user_id, is_admin)
        if not row:
            raise ValidationError("Aktivita nenalezena", code="not_found", status=404)

        updates: Dict[str, Any] = {}
        for key in (
            "category",
            "activity_type",
            "goal",
            "description",
            "frequency_per_day",
            "frequency_per_week",
        ):
            if key in validated:
                updates[key] = validated[key]

        if updates:
            activities_repo.update_activity(activity_id, updates, user_id, is_admin)
        else:
            return {"message": "No changes detected"}, 200

        entry_updates: Dict[str, Any] = {}
        if "description" in validated:
            entry_updates["description"] = validated["description"]
        if "category" in validated:
            entry_updates["category"] = validated["category"]
        if "activity_type" in validated:
            entry_updates["activity_type"] = validated["activity_type"]
        if "goal" in validated:
            entry_updates["goal"] = validated["goal"]
        if entry_updates:
            activities_repo.update_entries_for_activity(
                row["name"],
                entry_updates,
                row["user_id"],
            )

    if invalidate_cache_cb:
        invalidate_cache_cb("today")
        invalidate_cache_cb("stats")
    return {"message": "Aktivita aktualizována"}, 200


def deactivate_activity(
    activity_id: int,
    *,
    user_id: Optional[int],
    is_admin: bool,
    invalidate_cache_cb=None,
) -> Tuple[Dict[str, str], int]:
    deactivation_date = datetime.now().strftime("%Y-%m-%d")

    rowcount = activities_repo.deactivate_activity(activity_id, deactivation_date, user_id, is_admin)
    if rowcount == 0:
        raise ValidationError("Aktivita nenalezena", code="not_found", status=404)
    if invalidate_cache_cb:
        invalidate_cache_cb("today")
        invalidate_cache_cb("stats")
    return {"message": "Aktivita deaktivována"}, 200


def activate_activity(
    activity_id: int,
    *,
    user_id: Optional[int],
    is_admin: bool,
    invalidate_cache_cb=None,
) -> Tuple[Dict[str, str], int]:
    rowcount = activities_repo.activate_activity(activity_id, user_id, is_admin)
    if rowcount == 0:
        raise ValidationError("Aktivita nenalezena", code="not_found", status=404)
    if invalidate_cache_cb:
        invalidate_cache_cb("today")
        invalidate_cache_cb("stats")
    return {"message": "Aktivita aktivována"}, 200


def delete_activity(
    activity_id: int,
    *,
    user_id: Optional[int],
    is_admin: bool,
    invalidate_cache_cb=None,
) -> Tuple[Dict[str, str], int]:
    with db_transaction():
        row = activities_repo.get_activity_by_id(activity_id, user_id, is_admin)
        if not row:
            raise ValidationError("Aktivita nenalezena", code="not_found", status=404)
        if row.get("active"):
            raise ValidationError("Aktivita musí být deaktivována před smazáním", code="invalid_state", status=400)

        rowcount = activities_repo.delete_activity(activity_id, user_id, is_admin)

    if rowcount == 0:
        raise ValidationError("Aktivita nenalezena", code="not_found", status=404)

    if invalidate_cache_cb:
        invalidate_cache_cb("today")
        invalidate_cache_cb("stats")
    return {"message": "Aktivita smazána"}, 200
