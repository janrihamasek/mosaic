"""
Stats service.

Computes today and progress statistics, including cache-aware retrieval and
aggregation logic.
"""

from collections import defaultdict
from datetime import datetime, timedelta, date as date_cls
from typing import Any, DefaultDict, Dict, List, Optional, Tuple

from infra.cache_manager import CacheScope
from repositories import entries_repo, stats_repo
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

    cache_scope = CacheScope(user_id=user_id, is_admin=is_admin)
    cache_key_parts = ("entries", target_date)
    cached = cache_get("today", cache_key_parts, scope=cache_scope)
    if cached is not None:
        return cached
    # Ensure per-user missing entries exist for the day
    try:
        entries_repo.create_missing_entries_for_day(user_id, target_date, is_admin)
    except SQLAlchemyError as exc:
        raise ValidationError(str(exc), code="database_error", status=500)

    rows = stats_repo.get_today_entries(user_id, is_admin, target_date)
    data = []
    for r in rows:
        item = dict(r)
        if item.get("user_id") != user_id:
            continue
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

    cache_scope = CacheScope(user_id=user_id, is_admin=is_admin)
    cache_key_parts = ("dashboard", target_date.isoformat())
    cached = cache_get("stats", cache_key_parts, scope=cache_scope)
    if cached is not None:
        return cached

    today_str = target_date.strftime("%Y-%m-%d")
    window_start = target_date - timedelta(days=29)
    window_dates = [
        (window_start + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(30)
    ]

    try:
        entries = entries_repo.list_entries(
            user_id=user_id,
            is_admin=is_admin,
            start_date=window_dates[0],
            end_date=today_str,
            activity_filter=None,
            category_filter=None,
            limit=10000,
            offset=0,
        )
    except SQLAlchemyError as exc:
        raise ValidationError(str(exc), code="database_error", status=500)

    positive_entries = [
        e for e in entries if (e.get("activity_type") or "positive") != "negative"
    ]
    negative_entries = [
        e for e in entries if (e.get("activity_type") or "positive") == "negative"
    ]

    def ratio(total_value: float, total_goal: float) -> float:
        if total_goal <= 0:
            return 0.0
        return min(max(total_value, 0.0) / total_goal, 1.0)

    daily_totals: Dict[str, Dict[str, float]] = defaultdict(
        lambda: {"value": 0.0, "goal": 0.0}
    )
    category_daily: Dict[str, Dict[str, Dict[str, float]]] = defaultdict(
        lambda: defaultdict(lambda: {"value": 0.0, "goal": 0.0})
    )
    category_counts: Dict[str, int] = defaultdict(int)
    activity_totals: Dict[str, Dict[str, Dict[str, float]]] = defaultdict(
        lambda: defaultdict(lambda: {"value": 0.0, "goal": 0.0})
    )

    for entry in positive_entries:
        day = entry.get("date") or today_str
        value = float(entry.get("value") or 0.0)
        goal = float(entry.get("goal") or 0.0)
        category = entry.get("category") or "Other"
        activity = entry.get("activity") or entry.get("name") or "Unknown"

        daily_totals[day]["value"] += value
        daily_totals[day]["goal"] += goal

        category_daily[category][day]["value"] += value
        category_daily[category][day]["goal"] += goal

        category_counts[category] += 1
        activity_totals[category][activity]["value"] += value
        activity_totals[category][activity]["goal"] += goal

    daily_completion: Dict[str, float] = {
        day: ratio(totals["value"], totals["goal"])
        for day, totals in daily_totals.items()
    }

    active_day_threshold = 0.5
    goal_completion_today = round(
        ratio(
            daily_totals.get(today_str, {}).get("value", 0.0),
            daily_totals.get(today_str, {}).get("goal", 0.0),
        )
        * 100,
        1,
    )

    def avg_completion_for_days(days: int) -> float:
        keys = set(
            (target_date - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(days)
        )
        total = sum(daily_completion.get(k, 0.0) for k in keys)
        return round(min((total / days) * 100, 100.0), 1) if days else 0.0

    avg_goal_fulfillment = {
        "last_7_days": avg_completion_for_days(7),
        "last_30_days": avg_completion_for_days(30),
    }

    active_days = sum(
        1
        for _day, completion in daily_completion.items()
        if completion >= active_day_threshold
    )
    active_days_ratio = {
        "active_days": active_days,
        "total_days": 30,
        "percent": round(min(active_days / 30 * 100, 100.0), 1),
    }

    total_distribution = sum(category_counts.values())
    activity_distribution: List[Dict[str, Any]] = []
    for category, count in category_counts.items():
        percent = (count / total_distribution * 100) if total_distribution else 0.0
        activity_distribution.append(
            {"category": category, "count": count, "percent": round(percent, 2)}
        )

    # Negative activities are excluded from progress ratios; report positives only.
    positive_vs_negative = {
        "positive": len(positive_entries),
        "negative": 0,
        "ratio": 1.0 if len(positive_entries) > 0 else 0.0,
    }

    avg_goal_fulfillment_by_category: List[Dict[str, Any]] = []
    for category, per_day in category_daily.items():
        def _cat_avg(days: int) -> float:
            keys = set(
                (target_date - timedelta(days=i)).strftime("%Y-%m-%d")
                for i in range(days)
            )
            total = sum(
                ratio(per_day.get(k, {}).get("value", 0.0), per_day.get(k, {}).get("goal", 0.0))
                for k in keys
            )
            return round(min((total / days) * 100, 100.0), 1) if days else 0.0

        avg_goal_fulfillment_by_category.append(
            {
                "category": category,
                "last_7_days": _cat_avg(7),
                "last_30_days": _cat_avg(30),
            }
        )

    top_consistent_activities_by_category: List[Dict[str, Any]] = []
    for category, activities in activity_totals.items():
        scored = []
        for name, totals in activities.items():
            score = ratio(totals["value"], totals["goal"]) * 100.0
            scored.append({"name": name, "consistency_percent": round(score, 1)})
        scored.sort(key=lambda item: item["consistency_percent"], reverse=True)
        top_consistent_activities_by_category.append(
            {"category": category, "activities": scored[:3]}
        )

    payload = {
        "goal_completion_today": goal_completion_today,
        "streak_length": active_days,
        "activity_distribution": activity_distribution,
        "avg_goal_fulfillment": avg_goal_fulfillment,
        "active_days_ratio": active_days_ratio,
        "positive_vs_negative": positive_vs_negative,
        "avg_goal_fulfillment_by_category": avg_goal_fulfillment_by_category,
        "top_consistent_activities_by_category": top_consistent_activities_by_category,
    }

    cache_set("stats", cache_key_parts, payload, stats_cache_ttl, scope=cache_scope)
    return payload
