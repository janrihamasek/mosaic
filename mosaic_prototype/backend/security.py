from collections import defaultdict, deque
from datetime import datetime, UTC
from threading import Lock
from typing import Any, Dict, Optional

from flask import current_app, jsonify, request
from pydantic import ValidationError as PydanticValidationError

from schemas import (
    ActivityCreatePayload,
    ActivityUpdatePayload,
    CSVImportPayload,
    EntryPayload,
    FinalizeDayPayload,
)


class SimpleRateLimiter:
    """Very small in-memory rate limiter suitable for a single-process dev setup."""

    def __init__(self):
        self._calls = defaultdict(deque)
        self._lock = Lock()

    def allow(self, key: str, limit: int, window_seconds: int) -> bool:
        now = datetime.now(UTC).timestamp()
        with self._lock:
            q = self._calls[key]
            while q and q[0] <= now - window_seconds:
                q.popleft()
            if len(q) >= limit:
                return False
            q.append(now)
            return True


rate_limiter = SimpleRateLimiter()


def rate_limit(endpoint_name: str, limit: int, window_seconds: int):
    """Check and enforce per-endpoint rate limiting."""
    identifier = (
        request.headers.get("X-API-Key")
        or request.remote_addr
        or "anonymous"
    )
    key = f"{identifier}:{endpoint_name}"
    if not rate_limiter.allow(key, limit, window_seconds):
        return jsonify({"error": "Too many requests"}), 429
    return None


def require_api_key():
    """Require API key when MOSAIC_API_KEY is set."""
    api_key: Optional[str] = current_app.config.get("API_KEY")
    if not api_key:
        return None

    public_endpoints = current_app.config.get("PUBLIC_ENDPOINTS", {"home"})
    if request.endpoint in public_endpoints:
        return None

    provided = (
        request.headers.get("X-API-Key")
        or request.args.get("api_key")
    )
    if provided != api_key:
        return jsonify({"error": "Unauthorized"}), 401
    return None


class ValidationError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


def _first_error_message(exc: PydanticValidationError) -> str:
    errors = exc.errors()
    missing_fields = [
        ".".join(str(part) for part in err.get("loc", []) if part != "__root__")
        for err in errors
        if err.get("type") == "missing"
    ]
    if missing_fields:
        return f"Missing required field(s): {', '.join(missing_fields)}"
    if errors:
        message = errors[0].get("msg")
        if message:
            return message
    return str(exc)


def validate_entry_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValidationError("Invalid JSON payload")

    try:
        data = EntryPayload.model_validate(payload)
    except PydanticValidationError as exc:
        raise ValidationError(_first_error_message(exc))

    return data.model_dump()


def validate_activity_create_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValidationError("Invalid JSON payload")

    try:
        data = ActivityCreatePayload.model_validate(payload)
    except PydanticValidationError as exc:
        raise ValidationError(_first_error_message(exc))

    result = data.model_dump()
    result["goal"] = data.computed_goal
    return result


def validate_activity_update_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValidationError("Invalid JSON payload")

    try:
        data = ActivityUpdatePayload.model_validate(payload)
    except PydanticValidationError as exc:
        raise ValidationError(_first_error_message(exc))

    return data.to_update_dict()


def validate_csv_import_payload(files) -> Any:
    file_obj = None
    if hasattr(files, "get"):
        file_obj = files.get("file")
    try:
        data = CSVImportPayload.model_validate({"file": file_obj})
    except PydanticValidationError as exc:
        raise ValidationError(_first_error_message(exc))
    return data.file


def validate_finalize_day_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValidationError("Invalid JSON payload")

    try:
        data = FinalizeDayPayload.model_validate(payload)
    except PydanticValidationError as exc:
        raise ValidationError(_first_error_message(exc))

    date_value = data.date or datetime.now().strftime("%Y-%m-%d")
    return {"date": date_value}
