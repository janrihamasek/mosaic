import app as app_module
from flask import Blueprint
from security import jwt_required, require_admin

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
    return app_module.list_users()


@admin_bp.delete("/users/<int:user_id>")
@jwt_required()
@require_admin
def admin_delete_user(user_id: int):
    return app_module.admin_delete_user(user_id)
