"""Repository responsible for statistical data queries and aggregation."""

from typing import Any, Dict, List, Optional

from db_utils import connection as sa_connection
from extensions import db


def _user_scope_clause(column: str, *, include_unassigned: bool = False) -> str:
    """Build a WHERE clause fragment for user scoping with optional unassigned inclusion."""
    clause = f"{column} = ?"
    if include_unassigned:
        clause = f"({clause} OR {column} IS NULL)"
    return clause


def get_progress_data(
    user_id: int, is_admin: bool, start_date: str, end_date: str
) -> List[dict]:
    """Aggregate progress data grouped by activity."""
    conn = sa_connection(db.engine)
    try:
        params: List[Any] = [start_date, end_date]
        where_clause = "WHERE e.date >= ? AND e.date <= ?"
        if user_id is not None:
            where_clause += (
                f" AND {_user_scope_clause('e.user_id', include_unassigned=is_admin)}"
            )
            params.append(user_id)

        rows = conn.execute(
            f"""
            SELECT
                e.activity AS activity,
                COALESCE(a.category, e.activity_category, '') AS category,
                COALESCE(a.activity_type, e.activity_type, 'positive') AS activity_type,
                COALESCE(SUM(e.value), 0) AS actual,
                COALESCE(a.goal, e.activity_goal, 0) AS target,
                COUNT(*) AS count
            FROM entries e
            LEFT JOIN activities a
              ON a.name = e.activity
             AND (a.user_id = e.user_id OR a.user_id IS NULL)
            {where_clause}
            GROUP BY activity, category, activity_type, target
            """,
            params,
        ).fetchall()
    finally:
        conn.close()

    return [dict(row) for row in rows]


def get_category_aggregates(
    user_id: int, is_admin: bool, start_date: str, end_date: str
) -> List[dict]:
    """Aggregate progress data grouped by category."""
    conn = sa_connection(db.engine)
    try:
        params: List[Any] = [start_date, end_date]
        where_clause = "WHERE e.date >= ? AND e.date <= ?"
        if user_id is not None:
            where_clause += (
                f" AND {_user_scope_clause('e.user_id', include_unassigned=is_admin)}"
            )
            params.append(user_id)

        rows = conn.execute(
            f"""
            SELECT
                COALESCE(a.category, e.activity_category, '') AS category,
                COALESCE(a.activity_type, e.activity_type, 'positive') AS activity_type,
                COALESCE(SUM(e.value), 0) AS actual,
                COALESCE(SUM(COALESCE(a.goal, e.activity_goal, 0)), 0) AS target,
                COUNT(DISTINCT e.activity) AS activity_count
            FROM entries e
            LEFT JOIN activities a
              ON a.name = e.activity
             AND (a.user_id = e.user_id OR a.user_id IS NULL)
            {where_clause}
            GROUP BY category, activity_type
            """,
            params,
        ).fetchall()
    finally:
        conn.close()

    return [dict(row) for row in rows]


def get_today_entries(user_id: int, is_admin: bool, date: str) -> List[dict]:
    """Fetch all entries for a specific date with activity metadata."""
    conn = sa_connection(db.engine)
    try:
        params: List[Any] = [date]
        where_clause = "WHERE e.date = ?"
        if user_id is not None:
            where_clause += f" AND {_user_scope_clause('COALESCE(e.user_id, a.user_id)', include_unassigned=is_admin)}"
            params.append(user_id)

        rows = conn.execute(
            f"""
            SELECT
                e.*,
                e.activity AS name,
                COALESCE(a.category, e.activity_category, '') AS category,
                COALESCE(a.goal, e.activity_goal, 0) AS goal,
                COALESCE(a.description, e.description, '') AS activity_description,
                COALESCE(a.activity_type, e.activity_type, 'positive') AS activity_type,
                COALESCE(a.active, TRUE) AS active
            FROM entries e
            LEFT JOIN activities a
              ON a.name = e.activity
             AND (a.user_id = e.user_id OR a.user_id IS NULL)
            {where_clause}
            ORDER BY e.activity ASC
            """,
            params,
        ).fetchall()
    finally:
        conn.close()

    return [dict(row) for row in rows]


def get_active_activities_for_today(
    user_id: int, is_admin: bool, date: str
) -> List[dict]:
    """Fetch active (or not-yet-deactivated) activities for a target date."""
    conn = sa_connection(db.engine)
    try:
        params: List[Any] = [date]
        where_clause = (
            "WHERE active = TRUE OR (deactivated_at IS NOT NULL AND ? < deactivated_at)"
        )
        if user_id is not None:
            where_clause += (
                f" AND {_user_scope_clause('user_id', include_unassigned=is_admin)}"
            )
            params.append(user_id)

        rows = conn.execute(
            f"""
            SELECT
                name,
                category,
                goal,
                description,
                activity_type,
                active
            FROM activities
            {where_clause}
            """,
            params,
        ).fetchall()
    finally:
        conn.close()

    return [dict(row) for row in rows]


def get_active_positive_goals_by_category(
    user_id: Optional[int], include_unassigned: bool
) -> List[dict]:
    """Retrieve positive active activity goals grouped by category."""
    conn = sa_connection(db.engine)
    try:
        params: List[Any] = []
        where_clause = "WHERE active = TRUE AND activity_type = 'positive'"
        if user_id is not None:
            where_clause += f" AND {_user_scope_clause('user_id', include_unassigned=include_unassigned)}"
            params.append(user_id)
        where_clause += " GROUP BY category"

        rows = conn.execute(
            f"""
            SELECT
                COALESCE(NULLIF(category, ''), 'Other') AS category,
                COALESCE(SUM(goal), 0) AS total_goal
            FROM activities
            {where_clause}
            """,
            params,
        ).fetchall()
    finally:
        conn.close()

    return [dict(row) for row in rows]


def get_daily_positive_totals(
    user_id: Optional[int], include_unassigned: bool, start_date: str, end_date: str
) -> List[dict]:
    """Retrieve daily totals for positive entries within a date range."""
    conn = sa_connection(db.engine)
    try:
        params: List[Any] = [start_date, end_date]
        where_clause = "WHERE date BETWEEN ? AND ? AND activity_type = 'positive'"
        if user_id is not None:
            where_clause += f" AND {_user_scope_clause('user_id', include_unassigned=include_unassigned)}"
            params.append(user_id)
        where_clause += " GROUP BY date"

        rows = conn.execute(
            f"""
            SELECT
                date,
                COALESCE(SUM(value), 0) AS total_value,
                COALESCE(SUM(activity_goal), 0) AS total_goal,
                COUNT(*) AS entry_count
            FROM entries
            {where_clause}
            """,
            params,
        ).fetchall()
    finally:
        conn.close()

    return [dict(row) for row in rows]


def get_category_daily_totals(
    user_id: Optional[int], include_unassigned: bool, start_date: str, end_date: str
) -> List[dict]:
    """Retrieve daily totals by category for positive entries."""
    conn = sa_connection(db.engine)
    try:
        params: List[Any] = [start_date, end_date]
        where_clause = "WHERE date BETWEEN ? AND ? AND activity_type = 'positive'"
        if user_id is not None:
            where_clause += f" AND {_user_scope_clause('user_id', include_unassigned=include_unassigned)}"
            params.append(user_id)
        where_clause += " GROUP BY date, category"

        rows = conn.execute(
            f"""
            SELECT
                date,
                COALESCE(NULLIF(activity_category, ''), 'Other') AS category,
                COALESCE(SUM(value), 0) AS total_value,
                COALESCE(SUM(activity_goal), 0) AS total_goal
            FROM entries
            {where_clause}
            """,
            params,
        ).fetchall()
    finally:
        conn.close()

    return [dict(row) for row in rows]


def get_positive_distribution(
    user_id: Optional[int], include_unassigned: bool, start_date: str, end_date: str
) -> List[dict]:
    """Retrieve entry distribution counts for positive entries grouped by category."""
    conn = sa_connection(db.engine)
    try:
        params: List[Any] = [start_date, end_date]
        where_clause = "WHERE date BETWEEN ? AND ? AND activity_type = 'positive'"
        if user_id is not None:
            where_clause += f" AND {_user_scope_clause('user_id', include_unassigned=include_unassigned)}"
            params.append(user_id)
        where_clause += " GROUP BY category"

        rows = conn.execute(
            f"""
            SELECT
                COALESCE(NULLIF(activity_category, ''), 'Other') AS category,
                COUNT(*) AS entry_count
            FROM entries
            {where_clause}
            """,
            params,
        ).fetchall()
    finally:
        conn.close()

    return [dict(row) for row in rows]


def get_frequent_categories(
    user_id: Optional[int],
    include_unassigned: bool,
    start_date: str,
    end_date: str,
    limit: int = 5,
) -> List[dict]:
    """Retrieve most frequent categories within a date range."""
    conn = sa_connection(db.engine)
    try:
        params: List[Any] = [start_date, end_date]
        where_clause = "WHERE date BETWEEN ? AND ?"
        if user_id is not None:
            where_clause += f" AND {_user_scope_clause('user_id', include_unassigned=include_unassigned)}"
            params.append(user_id)
        where_clause += " GROUP BY category ORDER BY entry_count DESC LIMIT ?"
        params.append(limit)

        rows = conn.execute(
            f"""
            SELECT
                COALESCE(NULLIF(activity_category, ''), 'Other') AS category,
                COUNT(*) AS entry_count
            FROM entries
            {where_clause}
            """,
            params,
        ).fetchall()
    finally:
        conn.close()

    return [dict(row) for row in rows]
