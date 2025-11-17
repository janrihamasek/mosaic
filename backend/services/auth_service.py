"""
Auth service.

Handles authentication flows (register, login, profile updates) and token
generation/validation with no Flask request/response objects.
"""

import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple

import jwt  # type: ignore[import]
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash

from audit import log_event
from repositories import users_repo
from security import (
    ValidationError,
    validate_login_payload,
    validate_register_payload,
    validate_user_update_payload,
)


def _serialize_user_row(row) -> dict:
    username = row["username"] if "username" in row.keys() else ""
    display_name = (row["display_name"] if "display_name" in row.keys() else "") or username
    created_at_value = row["created_at"] if "created_at" in row.keys() else None
    if isinstance(created_at_value, datetime):
        created_at_str = created_at_value.replace(
            tzinfo=created_at_value.tzinfo or timezone.utc
        ).isoformat()
    elif created_at_value:
        created_at_str = str(created_at_value)
    else:
        created_at_str = None

    return {
        "id": row["id"] if "id" in row.keys() else None,
        "username": username,
        "display_name": display_name,
        "is_admin": bool(row["is_admin"]) if "is_admin" in row.keys() else False,
        "created_at": created_at_str,
    }


def register_user(payload: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
    data = validate_register_payload(payload or {})
    username = data["username"]
    password_hash = generate_password_hash(data["password"])
    display_name = data.get("display_name") or username

    new_user_id: Optional[int] = None
    try:
        new_user_id = users_repo.create_user(
            username,
            password_hash,
            display_name,
            datetime.now(timezone.utc).isoformat(),
        )
    except IntegrityError:
        log_event(
            "auth.register_failed",
            "Username already exists",
            level="warning",
            context={"username": username},
        )
        raise ValidationError("Username already exists", code="conflict", status=409)

    log_event(
        "auth.register",
        "User registered",
        user_id=new_user_id,
        context={"username": username},
    )
    return {"message": "User registered"}, 201


def _create_access_token(
    user_id: int,
    username: str,
    *,
    is_admin: bool,
    display_name: Optional[str],
    jwt_secret: str,
    jwt_algorithm: str,
    jwt_exp_minutes: int,
) -> Tuple[str, str]:
    csrf_token = secrets.token_hex(16)
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "username": username,
        "csrf": csrf_token,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=int(jwt_exp_minutes))).timestamp()),
        "is_admin": bool(is_admin),
        "display_name": (display_name or "").strip(),
    }
    token = jwt.encode(payload, jwt_secret, algorithm=jwt_algorithm)
    return token, csrf_token


def authenticate_user(
    payload: Dict[str, Any],
    *,
    jwt_secret: str,
    jwt_algorithm: str,
    jwt_exp_minutes: int,
) -> Tuple[Dict[str, Any], int]:
    data = validate_login_payload(payload or {})

    row = None
    is_admin_flag = False
    display_name = None
    row = users_repo.get_user_by_username(data["username"])

    if not row or not check_password_hash(row["password_hash"], data["password"]):
        log_event(
            "auth.login_failed",
            "Invalid username or password",
            user_id=row["id"] if row else None,
            level="warning",
            context={"username": data["username"]},
        )
        raise ValidationError("Invalid username or password", code="invalid_credentials", status=401)

    if row and "is_admin" in row.keys():
        is_admin_flag = bool(row["is_admin"])
    if row and "display_name" in row.keys():
        display_name = row["display_name"]

    access_token, csrf_token = _create_access_token(
        row["id"],
        data["username"],
        is_admin=is_admin_flag,
        display_name=display_name,
        jwt_secret=jwt_secret,
        jwt_algorithm=jwt_algorithm,
        jwt_exp_minutes=jwt_exp_minutes,
    )
    log_event(
        "auth.login",
        "User logged in",
        user_id=row["id"],
        context={"username": data["username"], "is_admin": is_admin_flag},
    )
    return (
        {
            "access_token": access_token,
            "csrf_token": csrf_token,
            "token_type": "Bearer",
            "expires_in": int(jwt_exp_minutes) * 60,
            "display_name": display_name,
            "is_admin": is_admin_flag,
        },
        200,
    )


def get_user_profile(user_id: int) -> Dict[str, Any]:
    row = users_repo.get_user_by_id(user_id)
    if not row:
        raise ValidationError("User not found", code="not_found", status=404)
    return _serialize_user_row(row)


def update_user_profile(user_id: int, payload: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
    data = validate_user_update_payload(payload or {})

    updates: Dict[str, Any] = {}
    if "display_name" in data:
        updates["display_name"] = data["display_name"].strip()
    if "password" in data:
        updates["password_hash"] = generate_password_hash(data["password"])

    if not updates:
        return {"message": "No changes detected"}, 200

    users_repo.update_user(user_id, updates)
    row = users_repo.get_user_by_id(user_id)

    if not row:
        raise ValidationError("User not found", code="not_found", status=404)

    return {"message": "Profile updated", "user": _serialize_user_row(row)}, 200


def delete_user(user_id: int, *, invalidate_cache_cb=None) -> Tuple[Dict[str, Any], int]:
    rowcount = users_repo.delete_user(user_id)
    if rowcount == 0:
        raise ValidationError("User not found", code="not_found", status=404)

    if invalidate_cache_cb:
        invalidate_cache_cb("today")
        invalidate_cache_cb("stats")

    return {"message": "Account deleted"}, 200
