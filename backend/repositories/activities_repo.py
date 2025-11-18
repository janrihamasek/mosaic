"""Repository managing activity-related database operations."""

from typing import Any, Dict, List, Optional, Tuple

from db_utils import connection as sa_connection
from db_utils import transactional_connection
from extensions import db
from sqlalchemy.exc import IntegrityError


class RepositoryError(Exception):
    """Base repository error."""


class NotFoundError(RepositoryError):
    """Raised when an entity is not found."""


class ConflictError(RepositoryError):
    """Raised when an action conflicts with current state."""


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


def _fetch_activity_by_id(
    conn, activity_id: int, user_id: Optional[int], is_admin: bool
) -> Optional[dict]:
    where_clause = "id = ?"
    params: List[Any] = [activity_id]
    if not is_admin:
        where_clause += " AND " + _user_scope_clause(
            "user_id", include_unassigned=False
        )
        params.append(user_id)

    row = conn.execute(
        f"""
        SELECT
            id,
            name,
            user_id,
            active,
            category,
            activity_type,
            goal,
            description,
            frequency_per_day,
            frequency_per_week,
            deactivated_at
        FROM activities
        WHERE {where_clause}
        """,
        params,
    ).fetchone()
    return dict(row) if row else None


def _propagate_entries(
    conn, activity_name: str, owner_user_id: Optional[int], updates: Dict[str, Any]
) -> None:
    """Propagate selected activity fields to related entries."""
    key_map = {
        "description": "description",
        "category": "activity_category",
        "activity_type": "activity_type",
        "goal": "activity_goal",
    }
    assignments: List[str] = []
    params: List[Any] = []
    for key, column in key_map.items():
        if key in updates:
            assignments.append(f"{column} = ?")
            params.append(updates[key])

    if not assignments:
        return

    params.append(activity_name)
    where_clause = "activity = ?"
    if owner_user_id is not None:
        where_clause += " AND user_id = ?"
        params.append(owner_user_id)
    else:
        where_clause += " AND user_id IS NULL"

    conn.execute(
        f"UPDATE entries SET {', '.join(assignments)} WHERE {where_clause}",
        params,
    )


def insert_activity(
    user_id: int, payload: Dict[str, Any], overwrite_existing: bool = False
) -> Tuple[Dict[str, Any], int]:
    """Insert a new activity, optionally overwriting an existing one."""
    name = payload["name"]
    params = (
        name,
        payload["category"],
        payload["activity_type"],
        payload["goal"],
        payload["description"],
        payload["frequency_per_day"],
        payload["frequency_per_week"],
        user_id,
    )

    with transactional_connection(db.engine) as conn:
        try:
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
                params,
            )
            return {"message": "Kategorie přidána"}, 201
        except IntegrityError:
            if not overwrite_existing:
                raise ConflictError("exists")
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
                    payload["category"],
                    payload["activity_type"],
                    payload["goal"],
                    payload["description"],
                    payload["frequency_per_day"],
                    payload["frequency_per_week"],
                    name,
                    user_id,
                ),
            )
            return {"message": "Aktivita obnovena"}, 200


def update_activity(
    activity_id: int,
    user_id: Optional[int],
    is_admin: bool,
    updates: Dict[str, Any],
) -> Tuple[Dict[str, Any], int]:
    """Update an activity and propagate selected fields to entries."""
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
        return {"message": "No changes detected"}, 200

    with transactional_connection(db.engine) as conn:
        row = _fetch_activity_by_id(conn, activity_id, user_id, is_admin)
        if not row:
            raise NotFoundError("not_found")

        params.append(activity_id)
        where_clause = "id = ?"
        if not is_admin:
            where_clause += " AND user_id = ?"
            params.append(user_id)

        conn.execute(
            f"UPDATE activities SET {', '.join(assignments)} WHERE {where_clause}",
            params,
        )

        propagate_fields: Dict[str, Any] = {}
        for key in ("description", "category", "activity_type", "goal"):
            if key in updates:
                propagate_fields[key] = updates[key]
        if propagate_fields:
            _propagate_entries(conn, row["name"], row.get("user_id"), propagate_fields)

    return {"message": "Aktivita aktualizována"}, 200


def deactivate_activity(
    activity_id: int, deactivation_date: str, user_id: Optional[int], is_admin: bool
) -> Tuple[Dict[str, str], int]:
    """Deactivate an activity and set deactivation timestamp with state checks."""
    with transactional_connection(db.engine) as conn:
        row = _fetch_activity_by_id(conn, activity_id, user_id, is_admin)
        if not row:
            raise NotFoundError("not_found")
        if not row.get("active"):
            raise ConflictError("already_inactive")

        params: List[Any] = [deactivation_date, activity_id]
        where_clause = "id = ?"
        if not is_admin:
            where_clause += " AND user_id = ?"
            params.append(user_id)

        conn.execute(
            f"UPDATE activities SET active = FALSE, deactivated_at = ? WHERE {where_clause}",
            params,
        )
    return {"message": "Aktivita deaktivována"}, 200


def activate_activity(
    activity_id: int, user_id: Optional[int], is_admin: bool
) -> Tuple[Dict[str, str], int]:
    """Activate an activity with state checks."""
    with transactional_connection(db.engine) as conn:
        row = _fetch_activity_by_id(conn, activity_id, user_id, is_admin)
        if not row:
            raise NotFoundError("not_found")
        if row.get("active"):
            raise ConflictError("already_active")

        params: List[Any] = [activity_id]
        where_clause = "id = ?"
        if not is_admin:
            where_clause += " AND user_id = ?"
            params.append(user_id)

        conn.execute(
            f"UPDATE activities SET active = TRUE, deactivated_at = NULL WHERE {where_clause}",
            params,
        )
    return {"message": "Aktivita aktivována"}, 200


def delete_activity(
    activity_id: int, user_id: Optional[int], is_admin: bool
) -> Tuple[Dict[str, str], int]:
    """Delete an activity after ensuring it is inactive."""
    with transactional_connection(db.engine) as conn:
        row = _fetch_activity_by_id(conn, activity_id, user_id, is_admin)
        if not row:
            raise NotFoundError("not_found")
        if row.get("active"):
            raise ConflictError("active")

        params: List[Any] = [activity_id]
        where_clause = "id = ?"
        if not is_admin:
            where_clause += " AND user_id = ?"
            params.append(user_id)

        conn.execute(
            f"DELETE FROM activities WHERE {where_clause}",
            params,
        )
    return {"message": "Aktivita smazána"}, 200
