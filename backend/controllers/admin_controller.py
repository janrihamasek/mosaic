import app as app_module
from flask import Blueprint, g, jsonify
from security import jwt_required, require_admin, error_response
from services import admin_service

admin_bp = Blueprint("admin", __name__)


@admin_bp.get("/")
def home():
    return app_module.home()


@admin_bp.get("/metrics")
def metrics():
    return app_module.metrics()


@admin_bp.get("/healthz")
def health():
    return app_module.health()


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

    # Lazy import to avoid circulars during app setup
    from app import invalidate_cache  # type: ignore

    result, status = admin_service.delete_user(
        user_id,
        requester_id=current_user.get("id"),
        invalidate_cache_cb=invalidate_cache,
    )
    return jsonify(result), status
