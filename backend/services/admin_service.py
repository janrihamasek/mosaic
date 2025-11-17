"""
Admin service.

Encapsulates admin-only user management operations and related authorization
rules while keeping Flask types out of this layer.
"""

from typing import Dict, List, Optional, Tuple

from security import ValidationError
from .common import db_transaction, get_db_connection
from .auth_service import _serialize_user_row


def list_users() -> List[Dict]:
    conn = get_db_connection()
    try:
        rows = conn.execute(
            """
            SELECT
                id,
                username,
                COALESCE(NULLIF(display_name, ''), username) AS display_name,
                COALESCE(is_admin, FALSE) AS is_admin,
                created_at
            FROM users
            ORDER BY LOWER(username) ASC
            """
        ).fetchall()
    finally:
        conn.close()
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
    with db_transaction() as conn:
        cur = conn.execute("DELETE FROM users WHERE id = ?", (user_id,))

    if cur.rowcount == 0:
        raise ValidationError("User not found", code="not_found", status=404)

    if invalidate_cache_cb:
        invalidate_cache_cb("today")
        invalidate_cache_cb("stats")

    return {"message": f"User {user_id} deleted"}, 200
