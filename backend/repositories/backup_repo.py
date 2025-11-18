"""Repository managing backup and restore database interactions."""

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from db_utils import connection as sa_connection
from db_utils import transactional_connection
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


def ensure_settings_row() -> None:
    """Create backup_settings table and ensure a default row exists."""
    with transactional_connection(db.engine) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS backup_settings (
                id SERIAL PRIMARY KEY,
                enabled BOOLEAN NOT NULL DEFAULT FALSE,
                interval_minutes INTEGER NOT NULL DEFAULT 60,
                last_run TIMESTAMPTZ
            )
            """
        )
        has_row = conn.execute("SELECT 1 FROM backup_settings LIMIT 1").scalar()
        if not has_row:
            conn.execute(
                "INSERT INTO backup_settings (enabled, interval_minutes) VALUES (?, ?)",
                (False, 60),
            )


def fetch_settings() -> Optional[Dict[str, Any]]:
    """Fetch the single backup_settings row."""
    conn = sa_connection(db.engine)
    try:
        row = conn.execute(
            "SELECT id, enabled, interval_minutes, last_run FROM backup_settings ORDER BY id ASC LIMIT 1"
        ).fetchone()
    finally:
        conn.close()
    return dict(row) if row else None


def update_settings(enabled: bool, interval_minutes: int) -> None:
    """Update backup settings, inserting a row if absent."""
    with transactional_connection(db.engine) as conn:
        row = conn.execute(
            "SELECT id FROM backup_settings ORDER BY id ASC LIMIT 1"
        ).fetchone()
        if row:
            conn.execute(
                "UPDATE backup_settings SET enabled = ?, interval_minutes = ? WHERE id = ?",
                (enabled, interval_minutes, row["id"]),
            )
        else:
            conn.execute(
                "INSERT INTO backup_settings (enabled, interval_minutes) VALUES (?, ?)",
                (enabled, interval_minutes),
            )


def update_last_run(timestamp: datetime) -> None:
    """Persist the last run timestamp."""
    with transactional_connection(db.engine) as conn:
        conn.execute(
            "UPDATE backup_settings SET last_run = ?, enabled = enabled",
            (timestamp,),
        )


def fetch_database_payload() -> Dict[str, List[Dict[str, object]]]:
    """Return entries and activities ordered for backup export."""
    conn = sa_connection(db.engine)
    try:
        entries_result = conn.execute(
            "SELECT * FROM entries ORDER BY date ASC, id ASC"
        )
        entries = [dict(row) for row in entries_result.mappings().fetchall()]
        activities_result = conn.execute(
            "SELECT * FROM activities ORDER BY name ASC"
        )
        activities = [dict(row) for row in activities_result.mappings().fetchall()]
    finally:
        conn.close()
    return {"entries": entries, "activities": activities}
