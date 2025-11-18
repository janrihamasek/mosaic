"""
Activities service.

Houses activity creation, updates, activation/deactivation, deletion, and
propagation logic. Keep HTTP and Flask concerns out of this layer.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from audit import log_event
from repositories import activities_repo
from security import (
    ValidationError,
    validate_activity_create_payload,
    validate_activity_update_payload,
)
from sqlalchemy.exc import SQLAlchemyError
from .idempotency import lookup as idempotency_lookup
from .idempotency import store_response as idempotency_store_response


def list_activities(
    *,
    user_id: Optional[int],
    is_admin: bool,
    show_all: bool,
    limit: int,
    offset: int,
) -> List[Dict[str, Any]]:
    try:
        payload = activities_repo.list_activities(
            user_id, is_admin, show_all, limit, offset
        )
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
        response_payload, status_code = activities_repo.insert_activity(
            user_id,
            {
                "name": name,
                "category": category,
                "activity_type": activity_type,
                "goal": goal,
                "description": description,
                "frequency_per_day": frequency_per_day,
                "frequency_per_week": frequency_per_week,
            },
            overwrite_existing=overwrite_existing,
        )
    except activities_repo.ConflictError:
        log_event(
            "activity.create_failed",
            "Activity already exists",
            user_id=user_id,
            level="warning",
            context={"name": name},
        )
        raise ValidationError("Aktivita již existuje", code="conflict", status=409)
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

    try:
        response, status_code = activities_repo.update_activity(
            activity_id, user_id, is_admin, updates
        )
    except activities_repo.NotFoundError:
        raise ValidationError("Aktivita nenalezena", code="not_found", status=404)
    except SQLAlchemyError as exc:
        raise ValidationError(str(exc), code="database_error", status=500)

    if invalidate_cache_cb:
        invalidate_cache_cb("today")
        invalidate_cache_cb("stats")
    return response, status_code


def deactivate_activity(
    activity_id: int,
    *,
    user_id: Optional[int],
    is_admin: bool,
    invalidate_cache_cb=None,
) -> Tuple[Dict[str, str], int]:
    deactivation_date = datetime.now().strftime("%Y-%m-%d")

    try:
        response, status_code = activities_repo.deactivate_activity(
            activity_id, deactivation_date, user_id, is_admin
        )
    except activities_repo.NotFoundError:
        raise ValidationError("Aktivita nenalezena", code="not_found", status=404)
    except activities_repo.ConflictError:
        raise ValidationError(
            "Aktivita již deaktivována", code="invalid_state", status=400
        )
    except SQLAlchemyError as exc:
        raise ValidationError(str(exc), code="database_error", status=500)
    if invalidate_cache_cb:
        invalidate_cache_cb("today")
        invalidate_cache_cb("stats")
    return response, status_code


def activate_activity(
    activity_id: int,
    *,
    user_id: Optional[int],
    is_admin: bool,
    invalidate_cache_cb=None,
) -> Tuple[Dict[str, str], int]:
    try:
        response, status_code = activities_repo.activate_activity(
            activity_id, user_id, is_admin
        )
    except activities_repo.NotFoundError:
        raise ValidationError("Aktivita nenalezena", code="not_found", status=404)
    except activities_repo.ConflictError:
        raise ValidationError(
            "Aktivita již aktivní", code="invalid_state", status=400
        )
    except SQLAlchemyError as exc:
        raise ValidationError(str(exc), code="database_error", status=500)
    if invalidate_cache_cb:
        invalidate_cache_cb("today")
        invalidate_cache_cb("stats")
    return response, status_code


def delete_activity(
    activity_id: int,
    *,
    user_id: Optional[int],
    is_admin: bool,
    invalidate_cache_cb=None,
) -> Tuple[Dict[str, str], int]:
    try:
        response, status_code = activities_repo.delete_activity(
            activity_id, user_id, is_admin
        )
    except activities_repo.NotFoundError:
        raise ValidationError("Aktivita nenalezena", code="not_found", status=404)
    except activities_repo.ConflictError:
        raise ValidationError(
            "Aktivita musí být deaktivována před smazáním",
            code="invalid_state",
            status=400,
        )
    except SQLAlchemyError as exc:
        raise ValidationError(str(exc), code="database_error", status=500)

    if invalidate_cache_cb:
        invalidate_cache_cb("today")
        invalidate_cache_cb("stats")
    return response, status_code
