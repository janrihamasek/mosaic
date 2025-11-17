from typing import Any, Dict

from flask import Blueprint, current_app, g, jsonify, request

from security import jwt_required, rate_limit, error_response
from services import auth_service

auth_bp = Blueprint("auth", __name__)


@auth_bp.post("/register")
def register():
    limits = current_app.config["RATE_LIMITS"]["register"]
    limited = rate_limit("register", limits["limit"], limits["window"])
    if limited:
        return limited

    payload: Dict[str, Any] = request.get_json() or {}
    result, status = auth_service.register_user(payload)
    return jsonify(result), status


@auth_bp.post("/login")
def login():
    limits = current_app.config["RATE_LIMITS"]["login"]
    limited = rate_limit("login", limits["limit"], limits["window"])
    if limited:
        return limited

    payload: Dict[str, Any] = request.get_json() or {}
    config = current_app.config
    jwt_secret = config.get("JWT_SECRET", "")
    jwt_algorithm = config.get("JWT_ALGORITHM", "HS256")
    jwt_exp_minutes = int(config.get("JWT_EXP_MINUTES", 60))

    result, status = auth_service.authenticate_user(
        payload,
        jwt_secret=jwt_secret,
        jwt_algorithm=jwt_algorithm,
        jwt_exp_minutes=jwt_exp_minutes,
    )
    return jsonify(result), status


@auth_bp.get("/user")
@jwt_required()
def get_current_user():
    current_user = getattr(g, "current_user", None)
    if not current_user:
        return error_response("unauthorized", "Unauthorized", 401)
    payload = auth_service.get_user_profile(current_user["id"])
    return jsonify(payload)


@auth_bp.patch("/user")
@jwt_required()
def update_current_user():
    current_user = getattr(g, "current_user", None)
    if not current_user:
        return error_response("unauthorized", "Unauthorized", 401)
    payload: Dict[str, Any] = request.get_json(silent=True) or {}
    result, status = auth_service.update_user_profile(current_user["id"], payload)
    return jsonify(result), status


@auth_bp.delete("/user")
@jwt_required()
def delete_current_user():
    current_user = getattr(g, "current_user", None)
    if not current_user:
        return error_response("unauthorized", "Unauthorized", 401)

    # Lazy import to avoid circulars during app setup
    from app import invalidate_cache  # type: ignore

    result, status = auth_service.delete_user(current_user["id"], invalidate_cache_cb=invalidate_cache)
    return jsonify(result), status
