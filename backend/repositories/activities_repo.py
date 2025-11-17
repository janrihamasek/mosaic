"""Repository managing activity-related database operations."""

from typing import Any, Dict, List, Optional

from db_utils import connection as sa_connection
from db_utils import transactional_connection
from extensions import db


def _user_scope_clause(column: str, *, include_unassigned: bool = False) -> str:
    """Build a WHERE clause fragment for user scoping with optional unassigned inclusion."""
    clause = f"{column} = ?"
    if include_unassigned:
        clause = f"({clause} OR {column} IS NULL)"
    return clause


def list_activities(
    user_id: Optional[int],
    is_admin: bool,
    show_all: bool,
    limit: int,
    offset: int,
) -> List[dict]:
    """List activities based on user visibility and activity status flags."""
    conn = sa_connection(db.engine)
    try:
        params: List[Any] = []
        where_clauses: List[str] = []
        if user_id is not None:
            where_clauses.append(
                _user_scope_clause("user_id", include_unassigned=is_admin)
            )
            params.append(user_id)
        if not show_all:
            where_clauses.append("active = TRUE")

        where_sql = ""
        if where_clauses:
            where_sql = "WHERE " + " AND ".join(where_clauses)

        params.extend([limit, offset])
        query = f"""
            SELECT *
            FROM activities
            {where_sql}
            ORDER BY active DESC, category ASC, name ASC
            LIMIT ? OFFSET ?
        """
        rows = conn.execute(query, params).fetchall()
    finally:
        conn.close()

    payload: List[dict] = []
    for row in rows:
        item = dict(row)
        if "active" in item:
            item["active"] = 1 if bool(item["active"]) else 0
        payload.append(item)
    return payload


def create_activity(
    name: str,
    category: str,
    activity_type: str,
    goal: float,
    description: str,
    frequency_per_day: int,
    frequency_per_week: int,
    user_id: int,
) -> None:
    """Insert a new activity row."""
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
            VALUES (?, ?, ?, ?, ?, TRUE, ?, ?, NULL, ?)
            """,
            (
                name,
                category,
                activity_type,
                goal,
                description,
                frequency_per_day,
                frequency_per_week,
                user_id,
            ),
        )


def get_activity_by_id(
    activity_id: int, user_id: Optional[int], is_admin: bool
) -> Optional[dict]:
    """Fetch an activity by id with optional user scoping."""
    conn = sa_connection(db.engine)
    try:
        where_clause = "id = ?"
        params: List[Any] = [activity_id]
        if not is_admin:
            where_clause += " AND " + _user_scope_clause(
                "user_id", include_unassigned=False
            )
            params.append(user_id)

        row = conn.execute(
            f"SELECT id, name, user_id, active FROM activities WHERE {where_clause}",
            params,
        ).fetchone()
    finally:
        conn.close()

    return dict(row) if row else None


def update_activity(
    activity_id: int,
    updates: Dict[str, Any],
    user_id: Optional[int],
    is_admin: bool,
) -> int:
    """Update an activity's fields and return affected row count."""
    allowed_keys = {
        "category",
        "activity_type",
        "goal",
        "description",
        "frequency_per_day",
        "frequency_per_week",
    }
    assignments: List[str] = []
    params: List[Any] = []
    for key, value in updates.items():
        if key in allowed_keys:
            assignments.append(f"{key} = ?")
            params.append(value)

    if not assignments:
        return 0

    params.append(activity_id)
    where_clause = "id = ?"
    if not is_admin:
        where_clause += " AND user_id = ?"
        params.append(user_id)

    with transactional_connection(db.engine) as conn:
        result = conn.execute(
            f"UPDATE activities SET {', '.join(assignments)} WHERE {where_clause}",
            params,
        )
        return result.rowcount


def update_entries_for_activity(
    activity_name: str,
    entry_updates: Dict[str, Any],
    owner_user_id: Optional[int],
) -> int:
    """Propagate activity field updates to related entries and return affected row count."""
    key_map = {
        "description": "description",
        "category": "activity_category",
        "activity_type": "activity_type",
        "goal": "activity_goal",
    }
    assignments: List[str] = []
    params: List[Any] = []

    for key, column in key_map.items():
        if key in entry_updates:
            assignments.append(f"{column} = ?")
            params.append(entry_updates[key])

    if not assignments:
        return 0

    params.append(activity_name)
    where_clause = "activity = ?"
    if owner_user_id is not None:
        where_clause += " AND user_id = ?"
        params.append(owner_user_id)

    with transactional_connection(db.engine) as conn:
        result = conn.execute(
            f"UPDATE entries SET {', '.join(assignments)} WHERE {where_clause}",
            params,
        )
        return result.rowcount


def activate_activity(activity_id: int, user_id: Optional[int], is_admin: bool) -> int:
    """Activate an activity and clear deactivation timestamp."""
    params: List[Any] = [activity_id]
    where_clause = "id = ?"
    if not is_admin:
        where_clause += " AND user_id = ?"
        params.append(user_id)

    with transactional_connection(db.engine) as conn:
        result = conn.execute(
            f"UPDATE activities SET active = TRUE, deactivated_at = NULL WHERE {where_clause}",
            params,
        )
        return result.rowcount


def deactivate_activity(
    activity_id: int, deactivation_date: str, user_id: Optional[int], is_admin: bool
) -> int:
    """Deactivate an activity and set deactivation timestamp."""
    params: List[Any] = [deactivation_date, activity_id]
    where_clause = "id = ?"
    if not is_admin:
        where_clause += " AND user_id = ?"
        params.append(user_id)

    with transactional_connection(db.engine) as conn:
        result = conn.execute(
            f"UPDATE activities SET active = FALSE, deactivated_at = ? WHERE {where_clause}",
            params,
        )
        return result.rowcount


def delete_activity(activity_id: int, user_id: Optional[int], is_admin: bool) -> int:
    """Delete an activity row and return affected row count."""
    params: List[Any] = [activity_id]
    where_clause = "id = ?"
    if not is_admin:
        where_clause += " AND user_id = ?"
        params.append(user_id)

    with transactional_connection(db.engine) as conn:
        result = conn.execute(
            f"DELETE FROM activities WHERE {where_clause}",
            params,
        )
        return result.rowcount


def overwrite_activity(
    name: str,
    category: str,
    activity_type: str,
    goal: float,
    description: str,
    frequency_per_day: int,
    frequency_per_week: int,
    user_id: int,
) -> None:
    """Overwrite an existing activity matching by name and ownership or unassigned."""
    with transactional_connection(db.engine) as conn:
        conn.execute(
            """
            UPDATE activities
            SET
                category = ?,
                activity_type = ?,
                goal = ?,
                description = ?,
                frequency_per_day = ?,
                frequency_per_week = ?,
                deactivated_at = NULL,
                active = TRUE
            WHERE name = ? AND (user_id = ? OR user_id IS NULL)
            """,
            (
                category,
                activity_type,
                goal,
                description,
                frequency_per_day,
                frequency_per_week,
                name,
                user_id,
            ),
        )
