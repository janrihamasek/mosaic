"""
Entries service.

Handles entry listing, upserts, deletions, and day finalization with cache
coordination delegated to appropriate helpers.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from audit import log_event
from security import ValidationError, validate_entry_payload, validate_finalize_day_payload
from .common import db_transaction, get_db_connection
from .idempotency import lookup as idempotency_lookup, store_response as idempotency_store_response


def _user_scope_clause(column: str, *, include_unassigned: bool = False) -> str:
    clause = f"{column} = ?"
    if include_unassigned:
        clause = f"({clause} OR {column} IS NULL)"
    return clause


def list_entries(
    *,
    user_id: int,
    is_admin: bool,
    start_date: Optional[str],
    end_date: Optional[str],
    activity_filter: Optional[str],
    category_filter: Optional[str],
    limit: int,
    offset: int,
) -> List[Dict[str, Any]]:
    # validate dates
    try:
        if start_date:
            datetime.strptime(start_date, "%Y-%m-%d")
        if end_date:
            datetime.strptime(end_date, "%Y-%m-%d")
    except ValueError:
        raise ValidationError("Invalid date filter", code="invalid_query", status=400)

    conn = get_db_connection()
    try:
        clauses = []
        params: list = []
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
        result = conn.execute(query, params)
        return [dict(row) for row in result.fetchall()]
    except SQLAlchemyError as exc:
        raise ValidationError(str(exc), code="database_error", status=500)
    finally:
        conn.close()


def add_entry(
    *,
    user_id: int,
    payload: Dict[str, Any],
    idempotency_key: Optional[str],
    invalidate_cache_cb=None,
) -> Tuple[Dict[str, Any], int]:
    data = validate_entry_payload(payload or {})
    date = data["date"]
    activity = data["activity"]
    note = data["note"]
    float_value = data["value"]

    cached = idempotency_lookup(user_id, idempotency_key)
    if cached:
        return cached

    try:
        with db_transaction() as conn:
            activity_row = conn.execute(
                "SELECT category, goal, description, activity_type FROM activities WHERE name = ? AND user_id = ?",
                (activity, user_id),
            ).fetchone()
            if not activity_row:
                activity_row = conn.execute(
                    "SELECT category, goal, description, activity_type FROM activities WHERE name = ? AND user_id IS NULL",
                    (activity,),
                ).fetchone()

            description = activity_row["description"] if activity_row else ""
            activity_category = activity_row["category"] if activity_row else ""
            activity_goal = activity_row["goal"] if activity_row else 0
            activity_type_value = (activity_row["activity_type"] if activity_row else None) or "positive"

            existing_entry = conn.execute(
                "SELECT activity_category, activity_goal, activity_type FROM entries WHERE date = ? AND activity = ? AND user_id = ?",
                (date, activity, user_id),
            ).fetchone()
            if not existing_entry:
                existing_entry = conn.execute(
                    "SELECT activity_category, activity_goal, activity_type FROM entries WHERE date = ? AND activity = ? AND user_id IS NULL",
                    (date, activity),
                ).fetchone()
            if not activity_row and existing_entry:
                activity_category = existing_entry["activity_category"] or activity_category
                activity_goal = (
                    existing_entry["activity_goal"] if existing_entry["activity_goal"] is not None else activity_goal
                )
                activity_type_value = existing_entry["activity_type"] or activity_type_value
            if not activity_row:
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
                        (
                            activity,
                            activity_category or "",
                            "positive",
                            float(activity_goal or 0),
                            description or "",
                            1,
                            1,
                            user_id,
                        ),
                    )
                except IntegrityError:
                    pass

            update_cur = conn.execute(
                """
                UPDATE entries
                SET value = ?,
                    note = ?,
                    description = ?,
                    activity_category = ?,
                    activity_goal = ?,
                    activity_type = ?,
                    user_id = ?
                WHERE date = ? AND activity = ? AND user_id = ?
                """,
                (
                    float_value,
                    note,
                    description,
                    activity_category,
                    activity_goal,
                    activity_type_value,
                    user_id,
                    date,
                    activity,
                    user_id,
                ),
            )

            if update_cur.rowcount > 0:
                response_payload = {"message": "Záznam aktualizován"}
                status_code = 200
            else:
                update_cur = conn.execute(
                    """
                    UPDATE entries
                    SET value = ?,
                        note = ?,
                        description = ?,
                        activity_category = ?,
                        activity_goal = ?,
                        activity_type = ?,
                        user_id = ?
                    WHERE date = ? AND activity = ? AND user_id IS NULL
                    """,
                    (
                        float_value,
                        note,
                        description,
                        activity_category,
                        activity_goal,
                        activity_type_value,
                        user_id,
                        date,
                        activity,
                    ),
                )

                if update_cur.rowcount > 0:
                    response_payload = {"message": "Záznam aktualizován"}
                    status_code = 200
                else:
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
                            float_value,
                            note,
                            activity_category,
                            activity_goal,
                            activity_type_value,
                            user_id,
                        ),
                    )
                    response_payload = {"message": "Záznam uložen"}
                    status_code = 201
    except SQLAlchemyError as exc:
        raise ValidationError(str(exc), code="database_error", status=500)

    if invalidate_cache_cb:
        invalidate_cache_cb("today")
        invalidate_cache_cb("stats")
    idempotency_store_response(user_id, idempotency_key, response_payload, status_code)
    return response_payload, status_code


def delete_entry(
    entry_id: int,
    *,
    user_id: int,
    is_admin: bool,
    invalidate_cache_cb=None,
) -> Tuple[Dict[str, str], int]:
    try:
        with db_transaction() as conn:
            if is_admin:
                cur = conn.execute("DELETE FROM entries WHERE id = ?", (entry_id,))
            else:
                cur = conn.execute(
                    "DELETE FROM entries WHERE id = ? AND user_id = ?",
                    (entry_id, user_id),
                )
        if cur.rowcount == 0:
            log_event(
                "entry.delete_missing",
                "Entry delete attempted but not found",
                user_id=user_id,
                level="warning",
                context={"entry_id": entry_id, "as_admin": is_admin},
            )
            raise ValidationError("Záznam nenalezen", code="not_found", status=404)
    except SQLAlchemyError as exc:
        raise ValidationError(str(exc), code="database_error", status=500)

    if invalidate_cache_cb:
        invalidate_cache_cb("today")
        invalidate_cache_cb("stats")
    log_event(
        "entry.delete",
        "Entry deleted",
        user_id=user_id,
        context={"entry_id": entry_id, "as_admin": is_admin},
    )
    return {"message": "Záznam smazán"}, 200


def finalize_day(
    *,
    user_id: int,
    is_admin: bool,
    payload: Dict[str, Any],
    invalidate_cache_cb=None,
) -> Tuple[Dict[str, str], int]:
    data = validate_finalize_day_payload(payload or {})
    date = data["date"]

    with db_transaction() as conn:
        active_query = """
            SELECT name, description, category, goal, activity_type
            FROM activities
            WHERE active = TRUE
               OR (deactivated_at IS NOT NULL AND ? < deactivated_at)
        """
        active_params: list = [date]
        if user_id is not None:
            active_query += f" AND {_user_scope_clause('user_id', include_unassigned=is_admin)}"
            active_params.append(user_id)
        active_activities = conn.execute(active_query, active_params).fetchall()
        existing_query = "SELECT activity FROM entries WHERE date = ?"
        existing_params: list = [date]
        if user_id is not None:
            existing_query += f" AND {_user_scope_clause('user_id', include_unassigned=is_admin)}"
            existing_params.append(user_id)
        existing = conn.execute(existing_query, existing_params).fetchall()
        existing_names = {e["activity"] for e in existing}

        created = 0
        for a in active_activities:
            if a["name"] not in existing_names:
                activity_type_value = (a["activity_type"] or "positive") if "activity_type" in a.keys() else "positive"
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
                    VALUES (?, ?, ?, 0, '', ?, ?, ?, ?)
                    """,
                    (date, a["name"], a["description"], a["category"], a["goal"], activity_type_value, user_id),
                )
                created += 1
    if invalidate_cache_cb:
        invalidate_cache_cb("today")
        invalidate_cache_cb("stats")
    return {"message": f"{created} missing entries added for {date}"}, 200
