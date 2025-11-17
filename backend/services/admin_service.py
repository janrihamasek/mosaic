"""
Admin service.

Encapsulates admin-only user management operations and related authorization
rules while keeping Flask types out of this layer.
"""

from typing import Dict, List, Optional, Tuple

from repositories import users_repo
from security import ValidationError

from .auth_service import _serialize_user_row


def list_users() -> List[Dict]:
    rows = users_repo.list_all_users()
    return [_serialize_user_row(row) for row in rows]


def delete_user(
    user_id: int,
    *,
    requester_id: Optional[int] = None,
    invalidate_cache_cb=None,
) -> Tuple[Dict[str, str], int]:
    if requester_id is not None and requester_id == user_id:
        raise ValidationError(
            "Admins cannot delete their own account",
            code="invalid_operation",
            status=400,
        )
    rowcount = users_repo.delete_user(user_id)

    if rowcount == 0:
        raise ValidationError("User not found", code="not_found", status=404)

    if invalidate_cache_cb:
        invalidate_cache_cb("today")
        invalidate_cache_cb("stats")

    return {"message": f"User {user_id} deleted"}, 200
