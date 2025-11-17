from datetime import UTC, datetime
from functools import wraps
from typing import Any, Dict, Optional

from flask import current_app, g, jsonify, request
from infra import rate_limiter
from pydantic import ValidationError as PydanticValidationError
from schemas import (
    ActivityCreatePayload,
    ActivityUpdatePayload,
    CSVImportPayload,
    EntryPayload,
    FinalizeDayPayload,
    LoginPayload,
    RegisterPayload,
    UserUpdatePayload,
    WearableBatchPayload,
)
from werkzeug.datastructures import FileStorage


def rate_limit(endpoint_name: str, limit: int, window_seconds: int):
    """Wrapper for the infra rate limiter to be used in controllers."""
    user_obj = getattr(g, "current_user", None)
    if user_obj:
        identifier = f"user:{user_obj['id']}"
    else:
        identifier = (
            request.headers.get("X-API-Key") or request.remote_addr or "anonymous"
        )
    is_limited = rate_limiter.check_rate_limit(
        endpoint_name, identifier, limit, window_seconds
    )
    if is_limited:
        return error_response("too_many_requests", "Rate limit exceeded", 429)
    return None


def limit_request(endpoint_name: str, *, per_minute: int):
    """Convenience wrapper to limit requests per minute."""
    per_minute = max(int(per_minute), 1)
    return rate_limit(endpoint_name, per_minute, 60)


def require_api_key():
    """Require API key when MOSAIC_API_KEY is set."""
    api_key: Optional[str] = current_app.config.get("API_KEY")
    if not api_key:
        return None

    if request.method == "OPTIONS":
        return None

    public_endpoints = current_app.config.get("PUBLIC_ENDPOINTS", {"home"})
    if request.endpoint in public_endpoints:
        return None

    provided = request.headers.get("X-API-Key") or request.args.get("api_key")
    if provided != api_key:
        return error_response("unauthorized", "Unauthorized", 401)
    return None


def require_admin(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        user_obj = getattr(g, "current_user", None)
        if not user_obj or not user_obj.get("is_admin"):
            return error_response("forbidden", "Admin privileges required", 403)
        return fn(*args, **kwargs)

    return wrapped


def jwt_required():
    def decorator(fn):
        @wraps(fn)
        def wrapped(*args, **kwargs):
            if not getattr(g, "current_user", None):
                return error_response(
                    "unauthorized", "Missing or invalid access token", 401
                )
            return fn(*args, **kwargs)

        return wrapped

    return decorator


class ValidationError(Exception):
    def __init__(
        self,
        message: str,
        *,
        code: str = "invalid_input",
        status: int = 400,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status = status
        self.details = details or {}


def error_response(
    code: str,
    message: str,
    status: int,
    details: Optional[Dict[str, Any]] = None,
):
    payload = {
        "error": {
            "code": code,
            "message": message,
            "details": details or {},
        }
    }
    return jsonify(payload), status


def _extract_error_info(exc: PydanticValidationError) -> tuple[str, Dict[str, Any]]:
    errors = exc.errors()
    missing_fields = [
        ".".join(str(part) for part in err.get("loc", []) if part != "__root__")
        for err in errors
        if err.get("type") == "missing"
    ]
    if missing_fields:
        return (
            f"Missing required field(s): {', '.join(missing_fields)}",
            {"fields": missing_fields},
        )
    if errors:
        message = errors[0].get("msg") or ""
        if message.startswith("Value error, "):
            message = message.split(", ", 1)[1]
        if (
            message.startswith("Input should be")
            and errors[0].get("type") == "is_instance_of"
            and tuple(errors[0].get("loc") or ()) == ("file",)
        ):
            return "Missing CSV file", {}
        if message:
            return message, {}
    return str(exc), {}


def validate_entry_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValidationError("Invalid JSON payload", code="invalid_json")

    try:
        data = EntryPayload.model_validate(payload)
    except PydanticValidationError as exc:
        message, details = _extract_error_info(exc)
        raise ValidationError(message, details=details)

    return data.model_dump()


def validate_activity_create_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValidationError("Invalid JSON payload", code="invalid_json")

    try:
        data = ActivityCreatePayload.model_validate(payload)
    except PydanticValidationError as exc:
        message, details = _extract_error_info(exc)
        raise ValidationError(message, details=details)

    result = data.model_dump()
    goal_value = data.goal if data.goal is not None else data.computed_goal
    result["goal"] = goal_value
    return result


def validate_activity_update_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValidationError("Invalid JSON payload", code="invalid_json")

    try:
        data = ActivityUpdatePayload.model_validate(payload)
    except PydanticValidationError as exc:
        message, details = _extract_error_info(exc)
        raise ValidationError(message, details=details)

    return data.to_update_dict()


def validate_wearable_batch_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValidationError("Invalid JSON payload", code="invalid_json")

    try:
        data = WearableBatchPayload.model_validate(payload)
    except PydanticValidationError as exc:
        message, details = _extract_error_info(exc)
        raise ValidationError(message, details=details)

    return data.model_dump()


def validate_csv_import_payload(files) -> Any:
    file_obj = None
    if hasattr(files, "get"):
        file_obj = files.get("file")
    if not isinstance(file_obj, FileStorage) or not getattr(file_obj, "filename", None):
        raise ValidationError("Missing CSV file", code="missing_file")
    try:
        data = CSVImportPayload.model_validate({"file": file_obj})
    except PydanticValidationError as exc:
        message, details = _extract_error_info(exc)
        raise ValidationError(message, details=details)
    return data.file


def validate_user_update_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValidationError("Invalid JSON payload", code="invalid_json")

    try:
        data = UserUpdatePayload.model_validate(payload)
    except PydanticValidationError as exc:
        message, details = _extract_error_info(exc)
        raise ValidationError(message, details=details)

    return data.model_dump(exclude_none=True)


def validate_finalize_day_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValidationError("Invalid JSON payload", code="invalid_json")

    try:
        data = FinalizeDayPayload.model_validate(payload)
    except PydanticValidationError as exc:
        message, details = _extract_error_info(exc)
        raise ValidationError(message, details=details)

    date_value = data.date or datetime.now().strftime("%Y-%m-%d")
    return {"date": date_value}


def validate_register_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValidationError("Invalid JSON payload", code="invalid_json")

    try:
        data = RegisterPayload.model_validate(payload)
    except PydanticValidationError as exc:
        message, details = _extract_error_info(exc)
        raise ValidationError(message, details=details)
    return data.model_dump()


def validate_login_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValidationError("Invalid JSON payload", code="invalid_json")

    try:
        data = LoginPayload.model_validate(payload)
    except PydanticValidationError as exc:
        message, details = _extract_error_info(exc)
        raise ValidationError(message, details=details)
    return data.model_dump()
