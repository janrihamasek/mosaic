from typing import Any, Dict

from flask import Blueprint, jsonify, request, current_app

from security import rate_limit, ValidationError, error_response
from services import wearable_service
from app import _current_user_id

wearable_bp = Blueprint("wearable", __name__)


@wearable_bp.post("/ingest/wearable/batch")
def ingest_wearable_batch():
    user_id = _current_user_id()
    if user_id is None:
        return error_response("unauthorized", "Missing user context", 401)

    limits = current_app.config["RATE_LIMITS"].get("wearable_ingest", {"limit": 60, "window": 60})
    limited = rate_limit("wearable_ingest", limits["limit"], limits["window"])
    if limited:
        return limited

    payload: Dict[str, Any] = request.get_json() or {}
    try:
        result, status = wearable_service.ingest_batch(user_id, payload)
    except ValidationError as exc:
        return error_response(exc.code, exc.message, exc.status, exc.details)
    return jsonify(result), status
