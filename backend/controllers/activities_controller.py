from typing import Any, Dict

from flask import Blueprint, jsonify, request, g, current_app

from security import rate_limit, ValidationError, error_response
from services import activities_service
from controllers.helpers import (
    parse_pagination,
    current_user_id,
    is_admin_user,
    header_truthy,
)
from infra.cache_manager import invalidate_cache

activities_bp = Blueprint("activities", __name__)


@activities_bp.get("/activities")
def get_activities():
    user_id = current_user_id()
    is_admin = is_admin_user()
    if user_id is None:
        return error_response("unauthorized", "Missing user context", 401)

    show_all = request.args.get("all", "false").lower() in ("1", "true", "yes")
    try:
        pagination = parse_pagination()
    except ValidationError as exc:
        return error_response(exc.code, exc.message, exc.status, exc.details)

    try:
        activities = activities_service.list_activities(
            user_id=user_id,
            is_admin=is_admin,
            show_all=show_all,
            limit=pagination["limit"],
            offset=pagination["offset"],
        )
    except ValidationError as exc:
        return error_response(exc.code, exc.message, exc.status, exc.details)

    return jsonify(activities)


@activities_bp.post("/add_activity")
def add_activity():
    user_id = current_user_id()
    if user_id is None:
        return error_response("unauthorized", "Missing user context", 401)

    limits = current_app.config["RATE_LIMITS"]["add_activity"]
    limited = rate_limit("add_activity", limits["limit"], limits["window"])
    if limited:
        return limited

    idempotency_key = request.headers.get("X-Idempotency-Key")
    overwrite_requested = header_truthy(request.headers.get("X-Overwrite-Existing"))

    data: Dict[str, Any] = request.get_json() or {}
    try:
        result, status = activities_service.add_activity(
            user_id=user_id,
            payload=data,
            overwrite_existing=overwrite_requested,
            idempotency_key=idempotency_key,
            invalidate_cache_cb=invalidate_cache,
        )
    except ValidationError as exc:
        return error_response(exc.code, exc.message, exc.status, exc.details)

    return jsonify(result), status


@activities_bp.put("/activities/<int:activity_id>")
def update_activity(activity_id):
    user = getattr(g, "current_user", None)
    user_id = user["id"] if user else None
    is_admin = bool(user["is_admin"]) if user else False
    if user_id is None:
        return error_response("unauthorized", "Missing user context", 401)

    limits = current_app.config["RATE_LIMITS"]["update_activity"]
    limited = rate_limit("update_activity", limits["limit"], limits["window"])
    if limited:
        return limited

    data: Dict[str, Any] = request.get_json() or {}
    try:
        result, status = activities_service.update_activity(
            activity_id,
            user_id=user_id,
            is_admin=is_admin,
            payload=data,
            invalidate_cache_cb=invalidate_cache,
        )
    except ValidationError as exc:
        return error_response(exc.code, exc.message, exc.status, exc.details)

    return jsonify(result), status


@activities_bp.patch("/activities/<int:activity_id>/deactivate")
def deactivate_activity(activity_id: int):
    user = getattr(g, "current_user", None)
    user_id = user["id"] if user else None
    is_admin = bool(user["is_admin"]) if user else False
    if user_id is None:
        return error_response("unauthorized", "Missing user context", 401)

    limits = current_app.config["RATE_LIMITS"]["activity_status"]
    limited = rate_limit("activities_deactivate", limits["limit"], limits["window"])
    if limited:
        return limited
    try:
        result, status = activities_service.deactivate_activity(
            activity_id,
            user_id=user_id,
            is_admin=is_admin,
            invalidate_cache_cb=invalidate_cache,
        )
    except ValidationError as exc:
        return error_response(exc.code, exc.message, exc.status, exc.details)
    return jsonify(result), status


@activities_bp.patch("/activities/<int:activity_id>/activate")
def activate_activity(activity_id: int):
    user = getattr(g, "current_user", None)
    user_id = user["id"] if user else None
    is_admin = bool(user["is_admin"]) if user else False
    if user_id is None:
        return error_response("unauthorized", "Missing user context", 401)

    limits = current_app.config["RATE_LIMITS"]["activity_status"]
    limited = rate_limit("activities_activate", limits["limit"], limits["window"])
    if limited:
        return limited
    try:
        result, status = activities_service.activate_activity(
            activity_id,
            user_id=user_id,
            is_admin=is_admin,
            invalidate_cache_cb=invalidate_cache,
        )
    except ValidationError as exc:
        return error_response(exc.code, exc.message, exc.status, exc.details)
    return jsonify(result), status


@activities_bp.delete("/activities/<int:activity_id>")
def delete_activity(activity_id: int):
    user = getattr(g, "current_user", None)
    user_id = user["id"] if user else None
    is_admin = bool(user["is_admin"]) if user else False
    if user_id is None:
        return error_response("unauthorized", "Missing user context", 401)

    limits = current_app.config["RATE_LIMITS"]["delete_activity"]
    limited = rate_limit("delete_activity", limits["limit"], limits["window"])
    if limited:
        return limited
    try:
        result, status = activities_service.delete_activity(
            activity_id,
            user_id=user_id,
            is_admin=is_admin,
            invalidate_cache_cb=invalidate_cache,
        )
    except ValidationError as exc:
        return error_response(exc.code, exc.message, exc.status, exc.details)
    return jsonify(result), status
