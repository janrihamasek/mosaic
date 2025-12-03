"""Repository managing activity-related database operations."""

from datetime import datetime
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


def _serialize_activity_row(row: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize DB activity rows for API responses."""
    item = dict(row)
    if "active" in item:
        item["active"] = 1 if bool(item["active"]) else 0
    return item


def _build_activity_response(row: Dict[str, Any], message: str) -> Dict[str, Any]:
    payload = _serialize_activity_row(row)
    payload["message"] = message
    return payload


def list_activities(
    user_id: int,
    is_admin: bool,
    show_all: bool,
    limit: int,
    offset: int,
) -> List[dict]:
    """List activities for the current user."""
    conn = sa_connection(db.engine)
    try:
        params: List[Any] = []
        where_clauses: List[str] = []
        where_clauses.append("user_id = ?")
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

    return [_serialize_activity_row(dict(row)) for row in rows]


def _fetch_activity_by_id(conn, activity_id: int, user_id: int) -> Optional[dict]:
    where_clause = "id = ? AND user_id = ?"
    params: List[Any] = [activity_id, user_id]

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


def _fetch_activity_by_name(conn, name: str, user_id: int) -> Optional[dict]:
    row = conn.execute(
        """
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
        WHERE name = ? AND user_id = ?
        """,
        (name, user_id),
    ).fetchone()
    return dict(row) if row else None


def _propagate_entries(
    conn, activity_name: str, owner_user_id: int, updates: Dict[str, Any]
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
    where_clause += " AND user_id = ?"
    params.append(owner_user_id)

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
        if overwrite_existing:
            # Avoid IntegrityError/failed transactions: Postgres upsert by unique (user_id, name)
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
                ON CONFLICT (user_id, name) DO UPDATE SET
                    category = EXCLUDED.category,
                    activity_type = EXCLUDED.activity_type,
                    goal = EXCLUDED.goal,
                    description = EXCLUDED.description,
                    frequency_per_day = EXCLUDED.frequency_per_day,
                    frequency_per_week = EXCLUDED.frequency_per_week,
                    deactivated_at = NULL,
                    active = TRUE
                """,
                params,
            )
            row = _fetch_activity_by_name(conn, name, user_id)
            if not row:
                raise RepositoryError("Activity not found after overwrite")
            return _build_activity_response(row, "Kategorie aktualizována"), 200

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
            row = _fetch_activity_by_name(conn, name, user_id)
            if not row:
                raise RepositoryError("Activity not found after insert")
            return _build_activity_response(row, "Kategorie přidána"), 201
        except IntegrityError:
            raise ConflictError("exists")


def update_activity(
    activity_id: int,
    user_id: int,
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
        row = _fetch_activity_by_id(conn, activity_id, user_id)
        if not row:
            raise NotFoundError("not_found")

        params.append(activity_id)
        where_clause = "id = ? AND user_id = ?"
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
            _propagate_entries(conn, row["name"], row["user_id"], propagate_fields)

    return {"message": "Aktivita aktualizována"}, 200


def deactivate_activity(
    activity_id: int, deactivation_date: str, user_id: int, is_admin: bool
) -> Tuple[Dict[str, str], int]:
    """Deactivate an activity and set deactivation timestamp with state checks."""
    with transactional_connection(db.engine) as conn:
        row = _fetch_activity_by_id(conn, activity_id, user_id)
        if not row:
            raise NotFoundError("not_found")
        if not row.get("active"):
            raise ConflictError("already_inactive")

        params: List[Any] = [deactivation_date, activity_id, user_id]
        where_clause = "id = ? AND user_id = ?"

        conn.execute(
            f"UPDATE activities SET active = FALSE, deactivated_at = ? WHERE {where_clause}",
            params,
        )
    return {"message": "Aktivita deaktivována"}, 200


def activate_activity(
    activity_id: int, user_id: int, is_admin: bool
) -> Tuple[Dict[str, str], int]:
    """Activate an activity with state checks."""
    with transactional_connection(db.engine) as conn:
        row = _fetch_activity_by_id(conn, activity_id, user_id)
        if not row:
            raise NotFoundError("not_found")
        if row.get("active"):
            raise ConflictError("already_active")

        params: List[Any] = [activity_id, user_id]
        where_clause = "id = ? AND user_id = ?"

        conn.execute(
            f"UPDATE activities SET active = TRUE, deactivated_at = NULL WHERE {where_clause}",
            params,
        )
    return {"message": "Aktivita aktivována"}, 200


def delete_activity(
    activity_id: int, user_id: int, is_admin: bool
) -> Tuple[Dict[str, str], int]:
    """Delete an activity after ensuring it is inactive."""
    with transactional_connection(db.engine) as conn:
        row = _fetch_activity_by_id(conn, activity_id, user_id)
        if not row:
            raise NotFoundError("not_found")
        if row.get("is_system"):
            raise ConflictError("system_activity")
        if row.get("active"):
            raise ConflictError("active")

        params: List[Any] = [activity_id, user_id]
        where_clause = "id = ? AND user_id = ?"

        conn.execute(
            f"DELETE FROM activities WHERE {where_clause}",
            params,
        )
    return {"message": "Aktivita smazána"}, 200


def batch_update_activities(
    action: str, ids: List[int], user_id: int, is_admin: bool
) -> Dict[str, Any]:
    """
    Perform batch activate/deactivate/delete with per-item validation.

    Returns a summary with processed IDs and skipped records including reason.
    """
    processed: List[int] = []
    skipped: List[Dict[str, Any]] = []
    unique_ids = []
    seen = set()
    for item in ids or []:
        try:
            value = int(item)
        except (TypeError, ValueError):
            continue
        if value <= 0 or value in seen:
            continue
        seen.add(value)
        unique_ids.append(value)

    if not unique_ids:
        return {"processed": [], "skipped": []}

    deactivation_date = datetime.now().strftime("%Y-%m-%d")
    with transactional_connection(db.engine) as conn:
        for activity_id in unique_ids:
            row = _fetch_activity_by_id(conn, activity_id, user_id)
            if not row:
                skipped.append({"id": activity_id, "reason": "not_found"})
                continue
            if row.get("is_system"):
                skipped.append({"id": activity_id, "reason": "system_activity"})
                continue

            if action == "activate":
                if row.get("active"):
                    skipped.append({"id": activity_id, "reason": "already_active"})
                    continue
                params: List[Any] = [activity_id, user_id]
                where_clause = "id = ? AND user_id = ?"
                conn.execute(
                    f"UPDATE activities SET active = TRUE, deactivated_at = NULL WHERE {where_clause}",
                    params,
                )
            elif action == "deactivate":
                if not row.get("active"):
                    skipped.append({"id": activity_id, "reason": "already_inactive"})
                    continue
                params = [deactivation_date, activity_id, user_id]
                where_clause = "id = ? AND user_id = ?"
                conn.execute(
                    f"UPDATE activities SET active = FALSE, deactivated_at = ? WHERE {where_clause}",
                    params,
                )
            elif action == "delete":
                if row.get("active"):
                    skipped.append({"id": activity_id, "reason": "active"})
                    continue
                params = [activity_id, user_id]
                where_clause = "id = ? AND user_id = ?"
                conn.execute(
                    f"DELETE FROM activities WHERE {where_clause}",
                    params,
                )
            else:
                skipped.append({"id": activity_id, "reason": "unsupported_action"})
                continue
            processed.append(activity_id)

    return {"processed": processed, "skipped": skipped}
