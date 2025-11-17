"""
Activities service.

Houses activity creation, updates, activation/deactivation, deletion, and
propagation logic. Keep HTTP and Flask concerns out of this layer.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from audit import log_event
from security import ValidationError, validate_activity_create_payload, validate_activity_update_payload
from .common import db_transaction, get_db_connection
from .idempotency import lookup as idempotency_lookup, store_response as idempotency_store_response


def _user_scope_clause(column: str, *, include_unassigned: bool = False) -> str:
    clause = f"{column} = ?"
    if include_unassigned:
        clause = f"({clause} OR {column} IS NULL)"
    return clause


def list_activities(
    *,
    user_id: Optional[int],
    is_admin: bool,
    show_all: bool,
    limit: int,
    offset: int,
) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    try:
        params: list = []
        where_clauses = []
        if user_id is not None:
            where_clauses.append(_user_scope_clause("user_id", include_unassigned=is_admin))
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
        payload = []
        for row in rows:
            item = dict(row)
            if "active" in item:
                item["active"] = 1 if bool(item["active"]) else 0
            payload.append(item)
        return payload
    except SQLAlchemyError as exc:
        raise ValidationError(str(exc), code="database_error", status=500)
    finally:
        conn.close()


def add_activity(
    *,
    user_id: int,
    payload: Dict[str, Any],
    overwrite_existing: bool,
    idempotency_key: Optional[str],
    invalidate_cache_cb=None,
) -> Tuple[Dict[str, Any], int]:
    validated = validate_activity_create_payload(payload or {})
    name = validated["name"]
    category = validated["category"]
    activity_type = validated["activity_type"]
    goal = validated["goal"]
    description = validated["description"]
    frequency_per_day = validated["frequency_per_day"]
    frequency_per_week = validated["frequency_per_week"]

    cached = idempotency_lookup(user_id, idempotency_key)
    if cached:
        payload, status_code = cached
        return payload, status_code

    try:
        with db_transaction() as conn:
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
            response_payload = {"message": "Kategorie přidána"}
            status_code = 201
    except IntegrityError:
        if not overwrite_existing:
            log_event(
                "activity.create_failed",
                "Activity already exists",
                user_id=user_id,
                level="warning",
                context={"name": name},
            )
            raise ValidationError("Aktivita již existuje", code="conflict", status=409)
        try:
            with db_transaction() as conn:
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
        except SQLAlchemyError as exc:
            raise ValidationError(str(exc), code="database_error", status=500)
        else:
            response_payload = {"message": "Aktivita obnovena"}
            status_code = 200
    except SQLAlchemyError as exc:
        raise ValidationError(str(exc), code="database_error", status=500)

    if invalidate_cache_cb:
        invalidate_cache_cb("today")
        invalidate_cache_cb("stats")

    idempotency_store_response(user_id, idempotency_key, response_payload, status_code)
    log_event(
        "activity.create",
        "Activity created",
        user_id=user_id,
        context={"name": name, "category": category},
    )
    return response_payload, status_code


def update_activity(
    activity_id: int,
    *,
    user_id: Optional[int],
    is_admin: bool,
    payload: Dict[str, Any],
    invalidate_cache_cb=None,
) -> Tuple[Dict[str, Any], int]:
    validated = validate_activity_update_payload(payload or {})

    with db_transaction() as conn:
        select_query = "SELECT id, name, user_id FROM activities WHERE id = ?"
        select_params: list = [activity_id]
        if not is_admin:
            select_query += " AND " + _user_scope_clause("user_id", include_unassigned=False)
            select_params.append(user_id)
        row = conn.execute(select_query, select_params).fetchone()
        if not row:
            raise ValidationError("Aktivita nenalezena", code="not_found", status=404)

        owner_user_id = row["user_id"]

        update_clauses = []
        params = []
        for key in (
            "category",
            "activity_type",
            "goal",
            "description",
            "frequency_per_day",
            "frequency_per_week",
        ):
            if key in validated:
                update_clauses.append(f"{key} = ?")
                params.append(validated[key])

        if not update_clauses:
            return {"message": "No changes detected"}, 200

        params.append(activity_id)
        update_where = "id = ?"
        if not is_admin:
            update_where += " AND user_id = ?"
            params.append(user_id)
        conn.execute(f"UPDATE activities SET {', '.join(update_clauses)} WHERE {update_where}", params)

        entry_update_clauses = []
        entry_params = []
        if "description" in validated:
            entry_update_clauses.append("description = ?")
            entry_params.append(validated["description"])
        if "category" in validated:
            entry_update_clauses.append("activity_category = ?")
            entry_params.append(validated["category"])
        if "activity_type" in validated:
            entry_update_clauses.append("activity_type = ?")
            entry_params.append(validated["activity_type"])
        if "goal" in validated:
            entry_update_clauses.append("activity_goal = ?")
            entry_params.append(validated["goal"])
        if entry_update_clauses:
            entry_params.append(row["name"])
            entry_where = "activity = ?"
            if owner_user_id is not None:
                entry_where += " AND user_id = ?"
                entry_params.append(owner_user_id)
            conn.execute(
                f"UPDATE entries SET {', '.join(entry_update_clauses)} WHERE {entry_where}",
                entry_params,
            )

    if invalidate_cache_cb:
        invalidate_cache_cb("today")
        invalidate_cache_cb("stats")
    return {"message": "Aktivita aktualizována"}, 200


def deactivate_activity(
    activity_id: int,
    *,
    user_id: Optional[int],
    is_admin: bool,
    invalidate_cache_cb=None,
) -> Tuple[Dict[str, str], int]:
    deactivation_date = datetime.now().strftime("%Y-%m-%d")

    with db_transaction() as conn:
        params = [deactivation_date, activity_id]
        where_clause = "id = ?"
        if not is_admin:
            where_clause += " AND user_id = ?"
            params.append(user_id)
        cur = conn.execute(
            f"UPDATE activities SET active = FALSE, deactivated_at = ? WHERE {where_clause}",
            params,
        )
        if cur.rowcount == 0:
            raise ValidationError("Aktivita nenalezena", code="not_found", status=404)
    if invalidate_cache_cb:
        invalidate_cache_cb("today")
        invalidate_cache_cb("stats")
    return {"message": "Aktivita deaktivována"}, 200


def activate_activity(
    activity_id: int,
    *,
    user_id: Optional[int],
    is_admin: bool,
    invalidate_cache_cb=None,
) -> Tuple[Dict[str, str], int]:
    with db_transaction() as conn:
        params = [activity_id]
        where_clause = "id = ?"
        if not is_admin:
            where_clause += " AND user_id = ?"
            params.append(user_id)
        cur = conn.execute(
            f"UPDATE activities SET active = TRUE, deactivated_at = NULL WHERE {where_clause}",
            params,
        )
        if cur.rowcount == 0:
            raise ValidationError("Aktivita nenalezena", code="not_found", status=404)
    if invalidate_cache_cb:
        invalidate_cache_cb("today")
        invalidate_cache_cb("stats")
    return {"message": "Aktivita aktivována"}, 200


def delete_activity(
    activity_id: int,
    *,
    user_id: Optional[int],
    is_admin: bool,
    invalidate_cache_cb=None,
) -> Tuple[Dict[str, str], int]:
    with db_transaction() as conn:
        select_query = "SELECT id, active, user_id FROM activities WHERE id = ?"
        params: list = [activity_id]
        if not is_admin:
            select_query += " AND user_id = ?"
            params.append(user_id)
        row = conn.execute(select_query, params).fetchone()
        if not row:
            raise ValidationError("Aktivita nenalezena", code="not_found", status=404)
        if row["active"]:
            raise ValidationError("Aktivita musí být deaktivována před smazáním", code="invalid_state", status=400)

        delete_where = "id = ?"
        delete_params = [activity_id]
        if not is_admin:
            delete_where += " AND user_id = ?"
            delete_params.append(user_id)
        cur = conn.execute(f"DELETE FROM activities WHERE {delete_where}", delete_params)

    if cur.rowcount == 0:
        raise ValidationError("Aktivita nenalezena", code="not_found", status=404)

    if invalidate_cache_cb:
        invalidate_cache_cb("today")
        invalidate_cache_cb("stats")
    return {"message": "Aktivita smazána"}, 200
