from flask import Blueprint, g, jsonify, request, Response

from security import jwt_required, require_admin, error_response
from services import admin_service
from infra.cache_manager import invalidate_cache
from infra import metrics_manager
from infra import health_service
from app import SERVER_START_TIME

admin_bp = Blueprint("admin", __name__)


@admin_bp.get("/")
def home():
    from app import home as app_home  # local import to avoid circular import at module load

    return app_home()


@admin_bp.get("/metrics")
def metrics():
    if request.args.get("format") == "text":
        return Response(metrics_manager.get_metrics_text(), mimetype="text/plain")
    return jsonify(metrics_manager.get_metrics_json())


@admin_bp.get("/healthz")
def health():
    summary, healthy = health_service.build_health_summary(SERVER_START_TIME)
    status_code = 200 if healthy else 503
    return jsonify(summary), status_code


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
