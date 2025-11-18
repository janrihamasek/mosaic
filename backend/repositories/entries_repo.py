"""Repository coordinating entry storage and retrieval."""

from typing import Any, Dict, List, Optional, Tuple

from db_utils import connection as sa_connection
from db_utils import transactional_connection
from extensions import db
from sqlalchemy.exc import IntegrityError


class RepositoryError(Exception):
    """Base repository error."""


class NotFoundError(RepositoryError):
    """Raised when a repository resource is not found."""


class ConflictError(RepositoryError):
    """Raised when a repository action conflicts with existing data."""



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
    *,
    cache_scope=None,
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


def get_activity_metadata(
    activity_name: str, user_id: int, conn: Optional[Any] = None
) -> Optional[dict]:
    """Fetch activity metadata for a user-scoped or unassigned activity."""
    managed_conn = conn or sa_connection(db.engine)
    try:
        row = managed_conn.execute(
            """
            SELECT category, goal, description, activity_type
            FROM activities
            WHERE name = ? AND user_id = ?
            """,
            (activity_name, user_id),
        ).fetchone()
        if not row:
            row = managed_conn.execute(
                """
                SELECT category, goal, description, activity_type
                FROM activities
                WHERE name = ? AND user_id IS NULL
                """,
                (activity_name,),
            ).fetchone()
    finally:
        if conn is None:
            managed_conn.close()

    return dict(row) if row else None


def get_existing_entry(
    date: str, activity: str, user_id: int, conn: Optional[Any] = None
) -> Optional[dict]:
    """Fetch an existing entry by date/activity scoped to user or unassigned."""
    managed_conn = conn or sa_connection(db.engine)
    try:
        row = managed_conn.execute(
            """
            SELECT activity_category, activity_goal, activity_type
            FROM entries
            WHERE date = ? AND activity = ? AND user_id = ?
            """,
            (date, activity, user_id),
        ).fetchone()
        if not row:
            row = managed_conn.execute(
                """
                SELECT activity_category, activity_goal, activity_type
                FROM entries
                WHERE date = ? AND activity = ? AND user_id IS NULL
                """,
                (date, activity),
            ).fetchone()
    finally:
        if conn is None:
            managed_conn.close()

    return dict(row) if row else None


def create_activity_for_entry(
    activity_name: str,
    category: str,
    goal: float,
    description: str,
    user_id: int,
    conn: Optional[Any] = None,
) -> None:
    """Insert a new activity when one does not exist for an entry."""
    if conn is None:
        with transactional_connection(db.engine) as managed_conn:
            managed_conn.execute(
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
        return

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
    conn: Optional[Any] = None,
) -> int:
    """Update an entry scoped by date/activity/user (or unassigned) and return affected row count."""
    allowed_keys = {
        "value",
        "note",
        "description",
        "activity_category",
        "activity_goal",
        "activity_type",
        "user_id",
    }
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

    def _execute(target_conn):
        result = target_conn.execute(
            f"UPDATE entries SET {', '.join(assignments)} WHERE date = ? AND activity = ? AND {user_clause}",
            params,
        )
        return result.rowcount

    if conn is None:
        with transactional_connection(db.engine) as managed_conn:
            return _execute(managed_conn)
    return _execute(conn)


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
    conn: Optional[Any] = None,
) -> None:
    """Insert a new entry row."""
    if conn is None:
        with transactional_connection(db.engine) as managed_conn:
            managed_conn.execute(
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
        return

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


def upsert_entry(
    date: str, activity: str, value: float, note: str, user_id: int
) -> Tuple[str, int]:
    """
    Create or update an entry in a single transaction.

    Returns a tuple of ("created"|"updated", affected_rowcount).
    """
    with transactional_connection(db.engine) as conn:
        activity_row = get_activity_metadata(activity, user_id, conn=conn)

        description = activity_row["description"] if activity_row else ""
        activity_category = activity_row["category"] if activity_row else ""
        activity_goal = activity_row["goal"] if activity_row else 0
        activity_type_value = (
            activity_row["activity_type"] if activity_row else None
        ) or "positive"

        existing_entry = get_existing_entry(date, activity, user_id, conn=conn)
        if not activity_row and existing_entry:
            activity_category = existing_entry["activity_category"] or activity_category
            activity_goal = (
                existing_entry["activity_goal"]
                if existing_entry["activity_goal"] is not None
                else activity_goal
            )
            activity_type_value = existing_entry["activity_type"] or activity_type_value
        if not activity_row:
            try:
                create_activity_for_entry(
                    activity,
                    activity_category or "",
                    float(activity_goal or 0),
                    description or "",
                    user_id,
                    conn=conn,
                )
            except IntegrityError:
                pass

        updates = {
            "value": value,
            "note": note,
            "description": description,
            "activity_category": activity_category,
            "activity_goal": activity_goal,
            "activity_type": activity_type_value,
            "user_id": user_id,
        }

        rowcount = update_entry_by_date_and_activity(
            date, activity, user_id, updates, conn=conn
        )

        if rowcount > 0:
            return "updated", rowcount

        rowcount = update_entry_by_date_and_activity(
            date, activity, None, updates, conn=conn
        )
        if rowcount > 0:
            return "updated", rowcount

        create_entry(
            date,
            activity,
            value,
            note,
            description,
            activity_category,
            activity_goal,
            activity_type_value,
            user_id,
            conn=conn,
        )
        return "created", 1


def upsert_entry_with_metadata_check(
    user_id: int, date: str, activity: str, value: float, note: str
) -> Tuple[Dict[str, Any], int]:
    """
    Repository-level upsert wrapper used by the service layer.

    Runs atomic upsert and returns payload + status code mirroring existing
    add_entry behavior.
    """
    status, _rowcount = upsert_entry(date, activity, value, note, user_id)
    # Expire session state so subsequent ORM queries see raw SQL changes
    try:
        db.session.expire_all()
    except Exception:
        pass
    if status == "updated":
        return {"message": "Záznam aktualizován"}, 200
    return {"message": "Záznam uložen"}, 201


def delete_entry(entry_id: int, requester_user_id: int, is_admin: bool) -> Tuple[Dict[str, str], int]:
    """Delete an entry by id with optional user scoping."""
    params: List[Any] = [entry_id]
    query = "DELETE FROM entries WHERE id = ?"
    if not is_admin:
        query += " AND user_id = ?"
        params.append(requester_user_id)

    with transactional_connection(db.engine) as conn:
        result = conn.execute(query, params)
        if result.rowcount == 0:
            raise NotFoundError("not_found")
    return {"message": "Záznam smazán"}, 200


def delete_entry_by_id(entry_id: int, user_id: int, is_admin: bool) -> int:
    """Compatibility wrapper returning rowcount for legacy callers."""
    try:
        delete_entry(entry_id, user_id, is_admin)
    except NotFoundError:
        return 0
    return 1


def get_active_activities_for_date(
    date: str, user_id: Optional[int], is_admin: bool, conn: Optional[Any] = None
) -> List[dict]:
    """Fetch active or not-yet-deactivated activities for a given date and user scope."""
    managed_conn = conn or sa_connection(db.engine)
    try:
        params: List[Any] = [date]
        where_clause = "WHERE (active = TRUE OR (deactivated_at IS NOT NULL AND ? < deactivated_at))"
        if user_id is not None:
            where_clause += (
                f" AND {_user_scope_clause('user_id', include_unassigned=is_admin)}"
            )
            params.append(user_id)

        rows = managed_conn.execute(
            f"""
            SELECT name, description, category, goal, activity_type
            FROM activities
            {where_clause}
            """,
            params,
        ).fetchall()
    finally:
        if conn is None:
            managed_conn.close()

    return [dict(row) for row in rows]


def get_existing_activities_for_date(
    date: str, user_id: Optional[int], is_admin: bool, conn: Optional[Any] = None
) -> List[dict]:
    """Fetch existing activities for a date from entries with optional user scoping."""
    managed_conn = conn or sa_connection(db.engine)
    try:
        params: List[Any] = [date]
        where_clause = "WHERE date = ?"
        if user_id is not None:
            where_clause += (
                f" AND {_user_scope_clause('user_id', include_unassigned=is_admin)}"
            )
            params.append(user_id)

        rows = managed_conn.execute(
            f"SELECT activity FROM entries {where_clause}",
            params,
        ).fetchall()
    finally:
        if conn is None:
            managed_conn.close()

    return [dict(row) for row in rows]


def bulk_create_entries(entries: List[Dict[str, Any]], conn: Optional[Any] = None) -> int:
    """Insert multiple entry rows in a single transaction; returns count inserted."""
    if not entries:
        return 0

    def _insert_all(target_conn):
        inserted = 0
        for entry in entries:
            target_conn.execute(
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

    if conn is None:
        with transactional_connection(db.engine) as managed_conn:
            return _insert_all(managed_conn)
    return _insert_all(conn)


def create_missing_entries_for_day(
    user_id: int, date: str, is_admin: bool
) -> int:
    """Ensure every active activity has an entry for the given date."""
    with transactional_connection(db.engine) as conn:
        active_activities = get_active_activities_for_date(
            date, user_id, is_admin, conn=conn
        )
        existing = get_existing_activities_for_date(date, user_id, is_admin, conn=conn)
        existing_names = {e["activity"] for e in existing}

        new_entries: List[Dict[str, Any]] = []
        for activity_row in active_activities:
            activity_name = activity_row["name"]
            if activity_name in existing_names:
                continue

            activity_type_value = (
                (activity_row.get("activity_type") or "positive")
                if isinstance(activity_row, dict)
                else "positive"
            )
            new_entries.append(
                {
                    "date": date,
                    "activity": activity_name,
                    "description": activity_row["description"],
                    "value": 0,
                    "note": "",
                    "activity_category": activity_row["category"],
                    "activity_goal": activity_row["goal"],
                    "activity_type": activity_type_value,
                    "user_id": user_id,
                }
            )

        created = bulk_create_entries(new_entries, conn=conn) if new_entries else 0
        return created


def _fetch_activity_for_import(name: str, conn) -> Optional[Dict[str, Any]]:
    """Retrieve activity row for import with all relevant metadata."""
    row = conn.execute(
        """
        SELECT
            id,
            name,
            category,
            COALESCE(activity_type, 'positive') AS activity_type,
            goal,
            description,
            COALESCE(active, TRUE) AS active,
            frequency_per_day,
            frequency_per_week,
            deactivated_at,
            user_id
        FROM activities
        WHERE name = ?
        """,
        (name,),
    ).fetchone()
    return dict(row) if row else None


def _ensure_activity_for_import(
    parsed_row: Dict[str, Any], user_id: Optional[int], conn
) -> Dict[str, Any]:
    """
    Create or update an activity for imported entries.

    Raises:
        ValueError: when the activity belongs to a different user.
    """
    activity_name = parsed_row["activity"]
    activity = _fetch_activity_for_import(activity_name, conn)

    if activity and user_id is not None:
        owner = activity.get("user_id")
        if owner not in (None, user_id):
            raise ValueError(f"Activity '{activity_name}' already belongs to another user")

    if activity is None:
        goal_value = float(parsed_row.get("goal") or 0)
        new_activity = {
            "name": activity_name,
            "category": parsed_row.get("category") or "",
            "activity_type": "positive",
            "goal": goal_value,
            "description": parsed_row.get("description") or "",
            "active": True,
            "frequency_per_day": parsed_row.get("frequency_per_day") or 1,
            "frequency_per_week": parsed_row.get("frequency_per_week") or 1,
            "deactivated_at": None,
            "user_id": user_id,
        }
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
                new_activity["name"],
                new_activity["category"],
                new_activity["activity_type"],
                new_activity["goal"],
                new_activity["description"],
                new_activity["frequency_per_day"],
                new_activity["frequency_per_week"],
                new_activity["user_id"],
            ),
        )
        return new_activity

    updates: List[str] = []
    params: List[Any] = []

    category = parsed_row.get("category") or ""
    if category and category != (activity.get("category") or ""):
        updates.append("category = ?")
        params.append(category)

    goal_value = float(parsed_row.get("goal") or 0)
    if goal_value != float(activity.get("goal") or 0):
        updates.append("goal = ?")
        params.append(goal_value)

    description = parsed_row.get("description") or ""
    if description and description != (activity.get("description") or ""):
        updates.append("description = ?")
        params.append(description)

    freq_day = parsed_row.get("frequency_per_day") or 1
    if freq_day != int(activity.get("frequency_per_day") or 0):
        updates.append("frequency_per_day = ?")
        params.append(freq_day)

    freq_week = parsed_row.get("frequency_per_week") or 1
    if freq_week != int(activity.get("frequency_per_week") or 0):
        updates.append("frequency_per_week = ?")
        params.append(freq_week)

    if not activity.get("active", True):
        updates.append("active = TRUE")
        updates.append("deactivated_at = NULL")

    if user_id is not None and activity.get("user_id") is None:
        updates.append("user_id = ?")
        params.append(user_id)

    if updates:
        params.append(activity["id"])
        conn.execute(
            f"UPDATE activities SET {', '.join(updates)} WHERE id = ?",
            params,
        )
        activity = _fetch_activity_for_import(activity_name, conn) or activity

    return activity


def _upsert_entry_for_import(
    parsed_row: Dict[str, Any], activity_row: Dict[str, Any], user_id: Optional[int], conn
) -> str:
    """Insert or update a single entry during CSV import."""
    activity_category = parsed_row.get("category") or activity_row.get("category") or ""
    activity_goal = (
        float(parsed_row.get("goal")) if parsed_row.get("goal") is not None else float(activity_row.get("goal") or 0)
    )
    description = parsed_row.get("description") or activity_row.get("description") or ""
    activity_type_value = activity_row.get("activity_type") or "positive"
    note_value = parsed_row.get("note") or ""

    entry_params: List[Any] = [parsed_row["date"], parsed_row["activity"]]
    entry_query = "SELECT id, user_id FROM entries WHERE date = ? AND activity = ?"
    if user_id is not None:
        entry_query += " AND user_id = ?"
        entry_params.append(user_id)

    existing_entry = conn.execute(entry_query, entry_params).fetchone()
    if existing_entry:
        existing_entry = dict(existing_entry)

    if not existing_entry:
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
                parsed_row["date"],
                parsed_row["activity"],
                description,
                float(parsed_row.get("value") or 0),
                note_value,
                activity_category,
                activity_goal,
                activity_type_value,
                user_id,
            ),
        )
        return "created"

    update_fields: List[str] = [
        "value = ?",
        "note = ?",
        "description = ?",
        "activity_category = ?",
        "activity_goal = ?",
        "activity_type = ?",
    ]
    update_params: List[Any] = [
        float(parsed_row.get("value") or 0),
        note_value,
        description,
        activity_category,
        activity_goal,
        activity_type_value,
    ]

    if user_id is not None and not existing_entry.get("user_id"):
        update_fields.append("user_id = ?")
        update_params.append(user_id)

    update_params.append(existing_entry["id"])
    conn.execute(
        f"UPDATE entries SET {', '.join(update_fields)} WHERE id = ?",
        update_params,
    )
    return "updated"


def import_entries_from_rows(
    rows: List[Dict[str, Any]], user_id: Optional[int]
) -> Tuple[int, int, int, List[Dict[str, Any]]]:
    """
    Import validated CSV rows into activities and entries tables.

    Returns:
        Tuple of (created_count, updated_count, skipped_count, details).
    """
    if not rows:
        return 0, 0, 0, []

    created = 0
    updated = 0
    skipped = 0
    details: List[Dict[str, Any]] = []

    with transactional_connection(db.engine) as conn:
        for row in rows:
            row_index = row.get("row")
            date_value = row.get("date")
            activity_name = row.get("activity")
            try:
                activity_row = _ensure_activity_for_import(row, user_id, conn)
            except ValueError as exc:
                skipped += 1
                details.append(
                    {
                        "row": row_index,
                        "date": date_value,
                        "activity": activity_name,
                        "status": "skipped",
                        "reason": str(exc),
                    }
                )
                continue

            status = _upsert_entry_for_import(row, activity_row, user_id, conn)
            if status == "created":
                created += 1
            else:
                updated += 1
            details.append(
                {
                    "row": row_index,
                    "date": date_value,
                    "activity": activity_name,
                    "status": status,
                }
            )
            # Run a second idempotent pass to validate consistency; counters unchanged.
            _upsert_entry_for_import(row, activity_row, user_id, conn)

    return created, updated, skipped, details
