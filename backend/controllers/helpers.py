from typing import Dict, Optional

from flask import g, request
from security import ValidationError


def current_user_id() -> Optional[int]:
    user = getattr(g, "current_user", None)
    return user["id"] if user else None


def is_admin_user() -> bool:
    user = getattr(g, "current_user", None)
    return bool(user["is_admin"]) if user and "is_admin" in user else False


def header_truthy(value: Optional[str]) -> bool:
    if value is None:
        return False
    return value.strip().lower() in ("1", "true", "yes", "force", "overwrite")


def parse_pagination(default_limit: int = 100, max_limit: int = 500) -> Dict[str, int]:
    try:
        limit_raw = request.args.get("limit", default_limit)
        limit = int(limit_raw)
        if limit <= 0:
            raise ValueError
    except (TypeError, ValueError):
        raise ValidationError("limit must be a positive integer", code="invalid_query")

    try:
        offset_raw = request.args.get("offset", 0)
        offset = int(offset_raw)
        if offset < 0:
            raise ValueError
    except (TypeError, ValueError):
        raise ValidationError(
            "offset must be a non-negative integer", code="invalid_query"
        )

    limit = min(limit, max_limit)
    return {"limit": limit, "offset": offset}
