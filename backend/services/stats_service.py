"""
Stats service.

Computes today and progress statistics, including cache-aware retrieval and
aggregation logic.
"""

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, DefaultDict, Dict, List, Optional, Tuple

from sqlalchemy.exc import SQLAlchemyError

from security import ValidationError
from .common import db_transaction, get_db_connection


def _user_scope_clause(column: str, *, include_unassigned: bool = False) -> str:
    clause = f"{column} = ?"
    if include_unassigned:
        clause = f"({clause} OR {column} IS NULL)"
    return clause


def get_today_payload(
    *,
    user_id: int,
    is_admin: bool,
    date: Optional[str],
    cache_get,
    cache_set,
    today_cache_ttl: int,
) -> List[Dict[str, Any]]:
    target_date = date or datetime.now().strftime("%Y-%m-%d")
    cache_scope = (user_id, is_admin)
    cache_key_parts = ("today", target_date)
    cached = cache_get("today", cache_key_parts, scope=cache_scope)
    if cached is not None:
        return cached

    conn = get_db_connection()
    try:
        params = [target_date]
        where_clause = "WHERE e.date = ?"
        if user_id is not None:
            where_clause += f" AND {_user_scope_clause('COALESCE(e.user_id, a.user_id)', include_unassigned=is_admin)}"
            params.append(user_id)

        query = f"""
            SELECT
                e.id,
                e.date,
                e.activity,
                e.description,
                e.value,
                e.note,
                COALESCE(a.category, e.activity_category, '') AS category,
                COALESCE(a.goal, e.activity_goal, 0) AS goal,
                COALESCE(a.activity_type, e.activity_type, 'positive') AS activity_type,
                e.activity_goal,
                e.activity_category,
                e.activity_type AS entry_activity_type,
                e.user_id,
                COALESCE(a.active, TRUE) AS active
            FROM entries e
            LEFT JOIN activities a
              ON a.name = e.activity
             AND (a.user_id = e.user_id OR a.user_id IS NULL)
            {where_clause}
            ORDER BY e.activity ASC
        """
        rows = conn.execute(query, params)
        rows = rows.fetchall()
        data = []
        for r in rows:
            item = dict(r)
            if "active" in item:
                item["active"] = 1 if bool(item["active"]) else 0
            if item.get("activity_type") == "negative":
                item["goal"] = 0
                if "activity_goal" in item:
                    item["activity_goal"] = 0
            data.append(item)
    finally:
        conn.close()
    cache_set("today", cache_key_parts, data, today_cache_ttl, scope=cache_scope)
    return data


def get_progress_stats(
    *,
    user_id: int,
    is_admin: bool,
    date: Optional[str],
    cache_get,
    cache_set,
    stats_cache_ttl: int,
) -> Dict[str, Any]:
    if date:
        try:
            target_date = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            raise ValidationError("Invalid date", code="invalid_query", status=400)
    else:
        target_date = datetime.now().date()

    cache_scope = (user_id, is_admin)
    cache_key_parts = ("dashboard", target_date.isoformat())
    cached = cache_get("stats", cache_key_parts, scope=cache_scope)
    if cached is not None:
        return cached

    today_str = target_date.strftime("%Y-%m-%d")
    window_30_start = (target_date - timedelta(days=29)).strftime("%Y-%m-%d")
    stats_include_unassigned = False

    conn = get_db_connection()
    try:
        activity_goal_sql = """
            SELECT
                COALESCE(NULLIF(category, ''), 'Other') AS category,
                COALESCE(SUM(goal), 0) AS total_goal
            FROM activities
            WHERE active = TRUE
              AND activity_type = 'positive'
        """
        activity_goal_params: list = []
        if user_id is not None:
            activity_goal_sql += f" AND {_user_scope_clause('user_id', include_unassigned=stats_include_unassigned)}"
            activity_goal_params.append(user_id)
        activity_goal_sql += "\n            GROUP BY category"
        activity_goal_rows = conn.execute(activity_goal_sql, activity_goal_params).fetchall()

        total_active_goal = 0.0
        category_goal_totals: Dict[str, float] = {}
        for row in activity_goal_rows:
            category_name = row["category"] or "Other"
            goal_value = max(float(row["total_goal"] or 0.0), 0.0)
            category_goal_totals[category_name] = goal_value
            total_active_goal += goal_value

        def compute_ratio(total_value: Optional[float]) -> float:
            if total_active_goal <= 0:
                return 0.0
            value = max(float(total_value or 0.0), 0.0)
            return min(value / total_active_goal, 1.0)

        daily_sql = """
            SELECT
                date,
                COALESCE(SUM(value), 0) AS total_value,
                COALESCE(SUM(activity_goal), 0) AS total_goal,
                COUNT(*) AS entry_count
            FROM entries
            WHERE date BETWEEN ? AND ?
              AND activity_type = 'positive'
        """
        daily_params: list = [window_30_start, today_str]
        if user_id is not None:
            daily_sql += f" AND {_user_scope_clause('user_id', include_unassigned=stats_include_unassigned)}"
            daily_params.append(user_id)
        daily_sql += "\n            GROUP BY date"
        daily_rows = conn.execute(daily_sql, daily_params).fetchall()

        daily_completion = {}
        for row in daily_rows:
            ratio = compute_ratio(row["total_value"])
            daily_completion[row["date"]] = ratio

        category_daily_sql = """
            SELECT
                date,
                COALESCE(NULLIF(activity_category, ''), 'Other') AS category,
                COALESCE(SUM(value), 0) AS total_value,
                COALESCE(SUM(activity_goal), 0) AS total_goal
            FROM entries
            WHERE date BETWEEN ? AND ?
              AND activity_type = 'positive'
        """
        category_daily_params: list = [window_30_start, today_str]
        if user_id is not None:
            category_daily_sql += f" AND {_user_scope_clause('user_id', include_unassigned=stats_include_unassigned)}"
            category_daily_params.append(user_id)
        category_daily_sql += "\n            GROUP BY date, category"
        category_daily_rows = conn.execute(category_daily_sql, category_daily_params).fetchall()

        categories_seen = set(category_goal_totals.keys())
        category_daily_completion: Dict[str, Dict[str, float]] = defaultdict(dict)
        for row in category_daily_rows:
            category = row["category"] or "Other"
            categories_seen.add(category)
            denominator = category_goal_totals.get(category, 0.0)
            if denominator <= 0:
                denominator = max(float(row["total_goal"] or 0.0), 0.0)
            total_value = max(float(row["total_value"] or 0.0), 0.0)
            if denominator <= 0:
                ratio = 0.0
            else:
                ratio = min(total_value / denominator, 1.0)
            category_daily_completion[category][row["date"]] = ratio

        streak_length = 0
        active_day_threshold = 0.5
        for offset in range(1, 31):
            key = (target_date - timedelta(days=offset)).strftime("%Y-%m-%d")
            if daily_completion.get(key, 0.0) >= active_day_threshold:
                streak_length += 1
            else:
                break

        goal_ratio_today = daily_completion.get(today_str, 0.0)
        goal_completion_today = round(min(goal_ratio_today * 100, 100.0), 1)

        distribution_sql = """
            SELECT
                COALESCE(NULLIF(activity_category, ''), 'Other') AS category,
                COUNT(*) AS entry_count
            FROM entries
            WHERE date BETWEEN ? AND ?
              AND activity_type = 'positive'
        """
        distribution_params: list = [window_30_start, today_str]
        if user_id is not None:
            distribution_sql += f" AND {_user_scope_clause('user_id', include_unassigned=stats_include_unassigned)}"
            distribution_params.append(user_id)
        distribution_sql += "\n            GROUP BY category"
        distribution_rows = conn.execute(distribution_sql, distribution_params).fetchall()

        distribution: Dict[str, int] = {}
        for row in distribution_rows:
            distribution[row["category"] or "Other"] = int(row["entry_count"] or 0)

        frequent_categories_sql = """
            SELECT
                COALESCE(NULLIF(activity_category, ''), 'Other') AS category,
                COUNT(*) AS entry_count
            FROM entries
            WHERE date BETWEEN ? AND ?
        """
        frequent_params: list = [window_30_start, today_str]
        if user_id is not None:
            frequent_categories_sql += f" AND {_user_scope_clause('user_id', include_unassigned=stats_include_unassigned)}"
            frequent_params.append(user_id)
        frequent_categories_sql += "\n            GROUP BY category ORDER BY entry_count DESC LIMIT 5"
        frequent_rows = conn.execute(frequent_categories_sql, frequent_params).fetchall()
        top_categories = [row["category"] or "Other" for row in frequent_rows]

        payload = {
            "goal_completion_today": goal_completion_today,
            "streak_length": streak_length,
            "category_goal_totals": category_goal_totals,
            "category_daily_completion": category_daily_completion,
            "daily_completion": daily_completion,
            "distribution": distribution,
            "top_categories": top_categories,
        }
    except SQLAlchemyError as exc:
        raise ValidationError(str(exc), code="database_error", status=500)
    finally:
        conn.close()

    cache_set("stats", cache_key_parts, payload, stats_cache_ttl, scope=cache_scope)
    return payload
