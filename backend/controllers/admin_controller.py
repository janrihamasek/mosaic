from flask import Blueprint, g, jsonify

from security import jwt_required, require_admin, error_response
from services import admin_service
from infra.cache_manager import invalidate_cache

admin_bp = Blueprint("admin", __name__)


@admin_bp.get("/")
def home():
    from app import home as app_home  # local import to avoid circular import at module load

    return app_home()


@admin_bp.get("/metrics")
def metrics():
    from app import metrics as app_metrics  # local import to avoid circular import at module load

    return app_metrics()


@admin_bp.get("/healthz")
def health():
    from app import health as app_health  # local import to avoid circular import at module load

    return app_health()


@admin_bp.get("/users")
@jwt_required()
@require_admin
def list_users():
    users = admin_service.list_users()
    return jsonify(users)


@admin_bp.delete("/users/<int:user_id>")
@jwt_required()
@require_admin
def admin_delete_user(user_id: int):
    current_user = getattr(g, "current_user", None)
    if not current_user:
        return error_response("unauthorized", "Unauthorized", 401)

    result, status = admin_service.delete_user(
        user_id,
        requester_id=current_user.get("id"),
        invalidate_cache_cb=invalidate_cache,
    )
    return jsonify(result), status
