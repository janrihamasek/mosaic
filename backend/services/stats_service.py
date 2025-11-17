"""
Stats service.

Computes today and progress statistics, including cache-aware retrieval and
aggregation logic.
"""

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, DefaultDict, Dict, List, Optional, Tuple

from repositories import stats_repo
from security import ValidationError
from sqlalchemy.exc import SQLAlchemyError


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
    rows = stats_repo.get_today_entries(user_id, is_admin, target_date)
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

    try:
        activity_goal_rows = stats_repo.get_active_positive_goals_by_category(
            user_id, stats_include_unassigned
        )

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

        daily_rows = stats_repo.get_daily_positive_totals(
            user_id, stats_include_unassigned, window_30_start, today_str
        )

        daily_completion = {}
        for row in daily_rows:
            ratio = compute_ratio(row["total_value"])
            daily_completion[row["date"]] = ratio

        category_daily_rows = stats_repo.get_category_daily_totals(
            user_id, stats_include_unassigned, window_30_start, today_str
        )

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

        distribution_rows = stats_repo.get_positive_distribution(
            user_id, stats_include_unassigned, window_30_start, today_str
        )

        distribution: Dict[str, int] = {}
        for row in distribution_rows:
            distribution[row["category"] or "Other"] = int(row["entry_count"] or 0)

        frequent_rows = stats_repo.get_frequent_categories(
            user_id, stats_include_unassigned, window_30_start, today_str
        )
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

    cache_set("stats", cache_key_parts, payload, stats_cache_ttl, scope=cache_scope)
    return payload
