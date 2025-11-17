from flask import Blueprint, g, jsonify, request
from infra.cache_manager import STATS_CACHE_TTL, TODAY_CACHE_TTL, cache_get, cache_set
from security import ValidationError, error_response
from services import stats_service

stats_bp = Blueprint("stats", __name__)


@stats_bp.get("/stats/progress")
def get_progress_stats():
    user = getattr(g, "current_user", None)
    user_id = user["id"] if user else None
    is_admin = bool(user["is_admin"]) if user else False
    if user_id is None:
        return error_response("unauthorized", "Missing user context", 401)

    date_raw = request.args.get("date")
    try:
        payload = stats_service.get_progress_stats(
            user_id=user_id,
            is_admin=is_admin,
            date=date_raw,
            cache_get=cache_get,
            cache_set=cache_set,
            stats_cache_ttl=STATS_CACHE_TTL,
        )
    except ValidationError as exc:
        return error_response(exc.code, exc.message, exc.status, exc.details)
    return jsonify(payload)
