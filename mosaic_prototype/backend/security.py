from collections import defaultdict, deque
from datetime import datetime, UTC
from threading import Lock
from typing import Any, Dict, Optional, Tuple

from flask import current_app, jsonify, request


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


def require_fields(payload: Dict[str, Any], fields: Tuple[str, ...]):
    missing = [f for f in fields if payload.get(f) is None]
    if missing:
        raise ValidationError(f"Missing required field(s): {', '.join(missing)}")


def ensure_date(value: str) -> str:
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except (ValueError, TypeError):
        raise ValidationError("Date must be in YYYY-MM-DD format")
    return value


def ensure_number(value: Any, field: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        raise ValidationError(f"{field} must be a number")


def ensure_int(value: Any, field: str, min_value: int = 0) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        raise ValidationError(f"{field} must be an integer")
    if number < min_value:
        raise ValidationError(f"{field} must be at least {min_value}")
    return number


def ensure_length(value: str, field: str, max_len: int):
    if value is None:
        return
    if len(value) > max_len:
        raise ValidationError(f"{field} must be at most {max_len} characters")


def validate_entry_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValidationError("Invalid JSON payload")

    require_fields(payload, ("date", "activity"))
    date = ensure_date(payload["date"])
    activity = payload["activity"].strip()
    if not activity:
        raise ValidationError("Activity must not be empty")

    value = ensure_number(payload.get("value", 0), "value")
    note = (payload.get("note") or "").strip()
    ensure_length(note, "note", 100)

    return {
        "date": date,
        "activity": activity,
        "value": value,
        "note": note,
    }


def validate_activity_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValidationError("Invalid JSON payload")

    require_fields(payload, ("name", "category", "goal"))
    name = payload["name"].strip()
    if not name:
        raise ValidationError("Activity name must not be empty")
    ensure_length(name, "name", 80)

    category = payload["category"].strip()
    if not category:
        raise ValidationError("Category must not be empty")
    ensure_length(category, "category", 80)

    goal = ensure_int(payload.get("goal"), "goal", min_value=0)

    description = (payload.get("description") or "").strip()
    ensure_length(description, "description", 180)

    return {
        "name": name,
        "category": category,
        "goal": goal,
        "description": description,
    }
