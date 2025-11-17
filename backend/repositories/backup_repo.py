"""Repository managing backup and restore database interactions."""

from typing import Any, Dict, List, Optional, Tuple

from db_utils import connection as sa_connection
from extensions import db


def _user_scope_clause(column: str, *, include_unassigned: bool = False) -> str:
    """Build a WHERE clause for user scoping with optional unassigned inclusion."""
    clause = f"{column} = ?"
    if include_unassigned:
        clause = f"({clause} OR {column} IS NULL)"
    return clause


def get_export_entries(
    user_id: Optional[int], is_admin: bool, limit: int, offset: int
) -> List[dict]:
    """Fetch entries for export with optional user scoping."""
    conn = sa_connection(db.engine)
    try:
        params: List[Any] = []
        where_clause = ""
        if user_id is not None:
            where_clause = (
                f"WHERE {_user_scope_clause('e.user_id', include_unassigned=is_admin)}"
            )
            params.append(user_id)
        params.extend([limit, offset])

        rows = conn.execute(
            f"""
            SELECT
                e.id AS entry_id,
                e.date,
                e.activity,
                e.description AS entry_description,
                e.value,
                e.note,
                e.activity_category,
                e.activity_goal,
                e.activity_type
            FROM entries e
            LEFT JOIN activities a
              ON a.name = e.activity
             AND (a.user_id = e.user_id OR a.user_id IS NULL)
            {where_clause}
            ORDER BY e.date ASC, e.id ASC
            LIMIT ? OFFSET ?
            """,
            params,
        ).fetchall()
    finally:
        conn.close()
    return [dict(row) for row in rows]


def get_export_activities(
    user_id: Optional[int], is_admin: bool, limit: int, offset: int
) -> List[dict]:
    """Fetch activities for export with optional user scoping."""
    conn = sa_connection(db.engine)
    try:
        params: List[Any] = []
        where_clause = ""
        if user_id is not None:
            where_clause = (
                f"WHERE {_user_scope_clause('a.user_id', include_unassigned=is_admin)}"
            )
            params.append(user_id)
        params.extend([limit, offset])

        rows = conn.execute(
            f"""
            SELECT
                a.id AS activity_id,
                a.name,
                a.category,
                a.activity_type,
                a.goal,
                a.description AS activity_description,
                a.active,
                a.frequency_per_day,
                a.frequency_per_week,
                a.deactivated_at
            FROM activities a
            {where_clause}
            ORDER BY a.name ASC, a.id ASC
            LIMIT ? OFFSET ?
            """,
            params,
        ).fetchall()
    finally:
        conn.close()
    return [dict(row) for row in rows]


def count_export_entries(user_id: Optional[int], is_admin: bool) -> int:
    """Count entries for export with optional user scoping."""
    conn = sa_connection(db.engine)
    try:
        if user_id is None:
            row = conn.execute("SELECT COUNT(1) FROM entries").fetchone()
        else:
            row = conn.execute(
                f"SELECT COUNT(1) FROM entries WHERE {_user_scope_clause('user_id', include_unassigned=is_admin)}",
                (user_id,),
            ).fetchone()
    finally:
        conn.close()
    return int(row[0]) if row else 0


def count_export_activities(user_id: Optional[int], is_admin: bool) -> int:
    """Count activities for export with optional user scoping."""
    conn = sa_connection(db.engine)
    try:
        if user_id is None:
            row = conn.execute("SELECT COUNT(1) FROM activities").fetchone()
        else:
            row = conn.execute(
                f"SELECT COUNT(1) FROM activities WHERE {_user_scope_clause('user_id', include_unassigned=is_admin)}",
                (user_id,),
            ).fetchone()
    finally:
        conn.close()
    return int(row[0]) if row else 0
