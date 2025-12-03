"""Repository managing backup and restore database interactions."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from db_utils import connection as sa_connection
from db_utils import transactional_connection
from extensions import db
from sqlalchemy import text


def get_export_entries(
    user_id: int, is_admin: bool, limit: int, offset: int
) -> List[dict]:
    """Fetch entries for export scoped to the current user."""
    conn = sa_connection(db.engine)
    try:
        params: List[Any] = [user_id]
        where_clause = "WHERE e.user_id = ?"
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
             AND a.user_id = e.user_id
            {where_clause}
            ORDER BY e.date ASC, e.id ASC
            LIMIT ? OFFSET ?
            """,
            params,
        ).fetchall()
    finally:
        conn.close()
    return [dict(row) for row in rows]


def get_export_entries_all(user_id: int, is_admin: bool) -> List[dict]:
    """Fetch all entries for backup/export (no pagination)."""
    return get_export_entries(user_id, is_admin, limit=10_000_000, offset=0)


def get_export_activities(
    user_id: int, is_admin: bool, limit: int, offset: int
) -> List[dict]:
    """Fetch activities for export scoped to the current user."""
    conn = sa_connection(db.engine)
    try:
        params: List[Any] = [user_id]
        where_clause = "WHERE a.user_id = ?"
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


def get_export_activities_all(user_id: int, is_admin: bool) -> List[dict]:
    return get_export_activities(user_id, is_admin, limit=10_000_000, offset=0)


def count_export_entries(user_id: int, is_admin: bool) -> int:
    """Count entries for export scoped to the current user."""
    conn = sa_connection(db.engine)
    try:
        row = conn.execute(
            "SELECT COUNT(1) FROM entries WHERE user_id = ?", (user_id,)
        ).fetchone()
    finally:
        conn.close()
    if not row:
        return 0
    # RowMapping may not support numeric indexing; use first value
    values = list(row.values()) if hasattr(row, "values") else list(row)
    count_value = values[0] if values else 0
    return int(count_value) if count_value is not None else 0  # type: ignore[arg-type]


def count_export_activities(user_id: int, is_admin: bool) -> int:
    """Count activities for export scoped to the current user."""
    conn = sa_connection(db.engine)
    try:
        row = conn.execute(
            "SELECT COUNT(1) FROM activities WHERE user_id = ?", (user_id,)
        ).fetchone()
    finally:
        conn.close()
    if not row:
        return 0
    values = list(row.values()) if hasattr(row, "values") else list(row)
    count_value = values[0] if values else 0
    return int(count_value) if count_value is not None else 0  # type: ignore[arg-type]


def ensure_settings_row(user_id: int) -> None:
    """Create backup_settings table and ensure a default row exists."""
    # Use a direct engine transaction to avoid issues with nested transactions
    # inside Flask session context during app startup/scheduler threads.
    with db.engine.begin() as raw_conn:
        raw_conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS backup_settings (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    enabled BOOLEAN NOT NULL DEFAULT FALSE,
                    interval_minutes INTEGER NOT NULL DEFAULT 60,
                    last_run TIMESTAMPTZ,
                    UNIQUE (user_id)
                )
                """
            )
        )
        has_row = raw_conn.execute(
            text("SELECT 1 FROM backup_settings WHERE user_id = :user_id LIMIT 1"),
            {"user_id": user_id},
        ).scalar()
        if not has_row:
            raw_conn.execute(
                text(
                    "INSERT INTO backup_settings (user_id, enabled, interval_minutes) VALUES (:user_id, :enabled, :interval)"
                ),
                {"user_id": user_id, "enabled": False, "interval": 60},
            )


def fetch_settings(user_id: int) -> Optional[Dict[str, Any]]:
    """Fetch the backup_settings row for the given user."""
    conn = sa_connection(db.engine)
    try:
        row = conn.execute(
            "SELECT id, enabled, interval_minutes, last_run FROM backup_settings WHERE user_id = ? ORDER BY id ASC LIMIT 1",
            (user_id,),
        ).fetchone()
    finally:
        conn.close()
    return dict(row) if row else None


def update_settings(user_id: int, enabled: bool, interval_minutes: int) -> None:
    """Update backup settings, inserting a row if absent for the user."""
    with transactional_connection(db.engine) as conn:
        row = conn.execute(
            "SELECT id FROM backup_settings WHERE user_id = ? ORDER BY id ASC LIMIT 1",
            (user_id,),
        ).fetchone()
        if row:
            conn.execute(
                "UPDATE backup_settings SET enabled = ?, interval_minutes = ? WHERE id = ?",
                (enabled, interval_minutes, row["id"]),
            )
        else:
            conn.execute(
                "INSERT INTO backup_settings (user_id, enabled, interval_minutes) VALUES (?, ?, ?)",
                (user_id, enabled, interval_minutes),
            )


def update_last_run(timestamp: datetime, user_id: int) -> None:
    """Persist the last run timestamp."""
    with transactional_connection(db.engine) as conn:
        conn.execute(
            "UPDATE backup_settings SET last_run = ?, enabled = enabled WHERE user_id = ?",
            (timestamp, user_id),
        )
