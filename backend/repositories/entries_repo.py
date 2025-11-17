"""Repository coordinating entry storage and retrieval."""

from typing import Any, Dict, List, Optional

from db_utils import transactional_connection
from db_utils import connection as sa_connection
from extensions import db


def _user_scope_clause(column: str, *, include_unassigned: bool = False) -> str:
    """Build a WHERE clause fragment for user scoping with optional unassigned inclusion."""
    clause = f"{column} = ?"
    if include_unassigned:
        clause = f"({clause} OR {column} IS NULL)"
    return clause


def list_entries(
    user_id: int,
    is_admin: bool,
    start_date: Optional[str],
    end_date: Optional[str],
    activity_filter: Optional[str],
    category_filter: Optional[str],
    limit: int,
    offset: int,
) -> List[dict]:
    """List entries with activity metadata joins and filtering."""
    conn = sa_connection(db.engine)
    try:
        clauses: List[str] = []
        params: List[Any] = []
        if start_date:
            clauses.append("e.date >= ?")
            params.append(start_date)
        if end_date:
            clauses.append("e.date <= ?")
            params.append(end_date)
        if activity_filter:
            clauses.append("e.activity = ?")
            params.append(activity_filter)
        if category_filter:
            clauses.append("COALESCE(a.category, e.activity_category, '') = ?")
            params.append(category_filter)
        if user_id is not None:
            clauses.append(_user_scope_clause("e.user_id", include_unassigned=is_admin))
            params.append(user_id)

        where_sql = ""
        if clauses:
            where_sql = "WHERE " + " AND ".join(clauses)

        query = f"""
            SELECT e.*,
                   COALESCE(a.category, e.activity_category, '') AS category,
                   COALESCE(a.goal, e.activity_goal, 0) AS goal,
                   COALESCE(a.description, e.description, '') AS activity_description,
                   COALESCE(a.activity_type, e.activity_type, 'positive') AS activity_type
            FROM entries e
            LEFT JOIN activities a
              ON a.name = e.activity
             AND (a.user_id = e.user_id OR a.user_id IS NULL)
            {where_sql}
            ORDER BY e.date DESC, e.activity ASC
            LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])
        rows = conn.execute(query, params).fetchall()
    finally:
        conn.close()

    return [dict(row) for row in rows]


def get_activity_metadata(activity_name: str, user_id: int) -> Optional[dict]:
    """Fetch activity metadata for a user-scoped or unassigned activity."""
    conn = sa_connection(db.engine)
    try:
        row = conn.execute(
            """
            SELECT category, goal, description, activity_type
            FROM activities
            WHERE name = ? AND user_id = ?
            """,
            (activity_name, user_id),
        ).fetchone()
        if not row:
            row = conn.execute(
                """
                SELECT category, goal, description, activity_type
                FROM activities
                WHERE name = ? AND user_id IS NULL
                """,
                (activity_name,),
            ).fetchone()
    finally:
        conn.close()

    return dict(row) if row else None


def get_existing_entry(date: str, activity: str, user_id: int) -> Optional[dict]:
    """Fetch an existing entry by date/activity scoped to user or unassigned."""
    conn = sa_connection(db.engine)
    try:
        row = conn.execute(
            """
            SELECT activity_category, activity_goal, activity_type
            FROM entries
            WHERE date = ? AND activity = ? AND user_id = ?
            """,
            (date, activity, user_id),
        ).fetchone()
        if not row:
            row = conn.execute(
                """
                SELECT activity_category, activity_goal, activity_type
                FROM entries
                WHERE date = ? AND activity = ? AND user_id IS NULL
                """,
                (date, activity),
            ).fetchone()
    finally:
        conn.close()

    return dict(row) if row else None


def create_activity_for_entry(activity_name: str, category: str, goal: float, description: str, user_id: int) -> None:
    """Insert a new activity when one does not exist for an entry."""
    with transactional_connection(db.engine) as conn:
        conn.execute(
            """
            INSERT INTO activities (
                name,
                category,
                activity_type,
                goal,
                description,
                active,
                frequency_per_day,
                frequency_per_week,
                deactivated_at,
                user_id
            )
            VALUES (?, ?, 'positive', ?, ?, TRUE, 1, 1, NULL, ?)
            """,
            (activity_name, category, goal, description, user_id),
        )


def update_entry_by_date_and_activity(
    date: str,
    activity: str,
    user_id: Optional[int],
    updates: Dict[str, Any],
) -> int:
    """Update an entry scoped by date/activity/user (or unassigned) and return affected row count."""
    allowed_keys = {"value", "note", "description", "activity_category", "activity_goal", "activity_type"}
    assignments: List[str] = []
    params: List[Any] = []
    for key, value in updates.items():
        if key in allowed_keys:
            assignments.append(f"{key} = ?")
            params.append(value)

    if not assignments:
        return 0

    params.extend([date, activity])
    user_clause = "user_id = ?"
    if user_id is None:
        user_clause = "user_id IS NULL"
    else:
        params.append(user_id)

    with transactional_connection(db.engine) as conn:
        result = conn.execute(
            f"UPDATE entries SET {', '.join(assignments)} WHERE date = ? AND activity = ? AND {user_clause}",
            params,
        )
        return result.rowcount


def create_entry(
    date: str,
    activity: str,
    value: float,
    note: str,
    description: str,
    activity_category: str,
    activity_goal: float,
    activity_type: str,
    user_id: int,
) -> None:
    """Insert a new entry row."""
    with transactional_connection(db.engine) as conn:
        conn.execute(
            """
            INSERT INTO entries (
                date,
                activity,
                description,
                value,
                note,
                activity_category,
                activity_goal,
                activity_type,
                user_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                date,
                activity,
                description,
                value,
                note,
                activity_category,
                activity_goal,
                activity_type,
                user_id,
            ),
        )


def delete_entry_by_id(entry_id: int, user_id: int, is_admin: bool) -> int:
    """Delete an entry by id with optional user scoping."""
    params: List[Any] = [entry_id]
    query = "DELETE FROM entries WHERE id = ?"
    if not is_admin:
        query += " AND user_id = ?"
        params.append(user_id)

    with transactional_connection(db.engine) as conn:
        result = conn.execute(query, params)
        return result.rowcount


def get_active_activities_for_date(date: str, user_id: Optional[int], is_admin: bool) -> List[dict]:
    """Fetch active or not-yet-deactivated activities for a given date and user scope."""
    conn = sa_connection(db.engine)
    try:
        params: List[Any] = [date]
        where_clause = "WHERE active = TRUE OR (deactivated_at IS NOT NULL AND ? < deactivated_at)"
        if user_id is not None:
            where_clause += f" AND {_user_scope_clause('user_id', include_unassigned=is_admin)}"
            params.append(user_id)

        rows = conn.execute(
            f"""
            SELECT name, description, category, goal, activity_type
            FROM activities
            {where_clause}
            """,
            params,
        ).fetchall()
    finally:
        conn.close()

    return [dict(row) for row in rows]


def get_existing_activities_for_date(date: str, user_id: Optional[int], is_admin: bool) -> List[dict]:
    """Fetch existing activities for a date from entries with optional user scoping."""
    conn = sa_connection(db.engine)
    try:
        params: List[Any] = [date]
        where_clause = "WHERE date = ?"
        if user_id is not None:
            where_clause += f" AND {_user_scope_clause('user_id', include_unassigned=is_admin)}"
            params.append(user_id)

        rows = conn.execute(
            f"SELECT activity FROM entries {where_clause}",
            params,
        ).fetchall()
    finally:
        conn.close()

    return [dict(row) for row in rows]


def bulk_create_entries(entries: List[Dict[str, Any]]) -> int:
    """Insert multiple entry rows in a single transaction; returns count inserted."""
    if not entries:
        return 0

    with transactional_connection(db.engine) as conn:
        inserted = 0
        for entry in entries:
            conn.execute(
                """
                INSERT INTO entries (
                    date,
                    activity,
                    description,
                    value,
                    note,
                    activity_category,
                    activity_goal,
                    activity_type,
                    user_id
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entry["date"],
                    entry["activity"],
                    entry["description"],
                    entry["value"],
                    entry["note"],
                    entry["activity_category"],
                    entry["activity_goal"],
                    entry["activity_type"],
                    entry["user_id"],
                ),
            )
            inserted += 1
    return inserted
