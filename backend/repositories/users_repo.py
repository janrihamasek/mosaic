"""Repository handling user data persistence and retrieval."""

from typing import Any, Dict, List, Optional

from sqlalchemy.exc import SQLAlchemyError

from db_utils import transactional_connection
from db_utils import connection as sa_connection
from extensions import db


def create_user(username: str, password_hash: str, display_name: str, created_at: str) -> int:
    """Insert a new user row and return its generated id."""
    new_user_id = 0
    with transactional_connection(db.engine) as conn:
        conn.execute(
            """
            INSERT INTO users (username, password_hash, display_name, created_at, is_admin)
            VALUES (?, ?, ?, ?, FALSE)
            """,
            (username, password_hash, display_name, created_at),
        )
        row = conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
        if row and "id" in row.keys():
            new_user_id = int(row["id"])
    return new_user_id


def get_user_by_username(username: str) -> Optional[dict]:
    """Fetch a user row by username, returning None when absent."""
    conn = sa_connection(db.engine)
    try:
        try:
            row = conn.execute(
                """
                SELECT
                    id,
                    password_hash,
                    COALESCE(is_admin, FALSE) AS is_admin,
                    COALESCE(NULLIF(display_name, ''), username) AS display_name
                FROM users
                WHERE username = ?
                """,
                (username,),
            ).fetchone()
        except SQLAlchemyError as exc:  # graceful fallback if is_admin column is missing
            if "is_admin" not in str(exc).lower():
                raise
            row = conn.execute(
                """
                SELECT
                    id,
                    password_hash,
                    FALSE AS is_admin,
                    username AS display_name
                FROM users
                WHERE username = ?
                """,
                (username,),
            ).fetchone()
    finally:
        conn.close()

    if not row:
        return None
    return dict(row)


def get_user_by_id(user_id: int) -> Optional[dict]:
    """Fetch a user row by id, returning None when absent."""
    conn = sa_connection(db.engine)
    try:
        row = conn.execute(
            """
            SELECT
                id,
                username,
                COALESCE(NULLIF(display_name, ''), username) AS display_name,
                COALESCE(is_admin, FALSE) AS is_admin,
                created_at
            FROM users
            WHERE id = ?
            """,
            (user_id,),
        ).fetchone()
    finally:
        conn.close()

    if not row:
        return None
    return dict(row)


def update_user(user_id: int, updates: Dict[str, Any]) -> int:
    """Update user fields from the provided mapping and return affected row count."""
    if not updates:
        return 0

    assignments: List[str] = []
    params: List[Any] = []
    for key, value in updates.items():
        assignments.append(f"{key} = ?")
        params.append(value)
    params.append(user_id)

    with transactional_connection(db.engine) as conn:
        result = conn.execute(
            f"UPDATE users SET {', '.join(assignments)} WHERE id = ?",
            params,
        )
        return result.rowcount


def delete_user(user_id: int) -> int:
    """Delete a user row by id and return affected row count."""
    with transactional_connection(db.engine) as conn:
        result = conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
        return result.rowcount


def list_all_users() -> List[dict]:
    """List all users ordered by username."""
    conn = sa_connection(db.engine)
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
            ORDER BY username
            """
        ).fetchall()
    finally:
        conn.close()

    return [dict(row) for row in rows]
