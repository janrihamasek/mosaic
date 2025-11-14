from datetime import datetime, date, timedelta, timezone
from typing import Dict, Optional

from flask import Blueprint, jsonify, request, g
from sqlalchemy import func
from sqlalchemy.sql import label

from extensions import db
from models import (
    WearableCanonicalHR,
    WearableCanonicalSleepSession,
    WearableDailyAgg,
)
from security import ValidationError, error_response, jwt_required
from schemas_wearable import (
    WearableDayResponse,
    WearableHrSummary,
    WearableSleepSummary,
    WearableTrendPoint,
    WearableTrendsQuery,
    WearableTrendsResponse,
)

wearable_read_bp = Blueprint("wearable_read", __name__)


def _current_user_id() -> Optional[int]:
    current = getattr(g, "current_user", None)
    if isinstance(current, dict):
        return current.get("id")
    return None


def _day_start_for(target_date: date) -> datetime:
    return datetime(target_date.year, target_date.month, target_date.day, tzinfo=timezone.utc)


def _parse_date_param(value: Optional[str]) -> date:
    if not value:
        return datetime.now(timezone.utc).date()
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        raise ValidationError("date must be in YYYY-MM-DD format", code="invalid_query")


def _validate_trends_query(metric: Optional[str], window: Optional[str]) -> WearableTrendsQuery:
    try:
        window_value = int(window) if window is not None else 7
    except (TypeError, ValueError):
        raise ValidationError("window must be an integer", code="invalid_query")
    payload = {
        "metric": metric or "steps",
        "window": window_value,
    }
    try:
        return WearableTrendsQuery.model_validate(payload)
    except Exception as exc:  # pylint: disable=broad-except
        raise ValidationError(str(exc), code="invalid_query")


@wearable_read_bp.route("/wearable/day", methods=["GET"])
@jwt_required()
def get_wearable_day():
    user_id = _current_user_id()
    if user_id is None:
        return error_response("unauthorized", "Missing or invalid access token", 401)
    target_date = _parse_date_param(request.args.get("date"))
    start = _day_start_for(target_date)
    end = start + timedelta(days=1)

    aggregate = db.session.query(
        func.coalesce(func.sum(WearableDailyAgg.steps), 0),
        func.coalesce(func.sum(WearableDailyAgg.sleep_seconds), 0),
        func.min(WearableDailyAgg.resting_heart_rate),
    ).filter(
        WearableDailyAgg.user_id == user_id,
        WearableDailyAgg.day_start_utc >= start,
        WearableDailyAgg.day_start_utc < end,
    ).one()

    steps_total = int(aggregate[0] or 0)
    sleep_seconds = int(aggregate[1] or 0)
    resting_hr = aggregate[2]

    sleep_stats = db.session.query(
        func.coalesce(func.sum(WearableCanonicalSleepSession.duration_seconds), 0),
        func.avg(WearableCanonicalSleepSession.score),
        func.count(WearableCanonicalSleepSession.id),
    ).filter(
        WearableCanonicalSleepSession.user_id == user_id,
        WearableCanonicalSleepSession.start_time_utc >= start,
        WearableCanonicalSleepSession.start_time_utc < end,
    ).one()

    efficiency = None
    if sleep_stats[1] is not None:
        efficiency = float(sleep_stats[1])
    sessions = int(sleep_stats[2] or 0)
    total_min = round(sleep_seconds / 60, 1)

    hr_stats = db.session.query(
        func.min(WearableCanonicalHR.bpm),
        func.avg(WearableCanonicalHR.bpm),
        func.max(WearableCanonicalHR.bpm),
    ).filter(
        WearableCanonicalHR.user_id == user_id,
        WearableCanonicalHR.timestamp_utc >= start,
        WearableCanonicalHR.timestamp_utc < end,
    ).one()

    hr_summary = WearableHrSummary(
        rest=resting_hr if resting_hr is not None else None,
        avg=float(hr_stats[1]) if hr_stats[1] is not None else None,
        min=int(hr_stats[0]) if hr_stats[0] is not None else None,
        max=int(hr_stats[2]) if hr_stats[2] is not None else None,
    )

    payload = WearableDayResponse(
        date=target_date.isoformat(),
        steps=steps_total,
        sleep=WearableSleepSummary(total_min=total_min, efficiency=efficiency, sessions=sessions),
        hr=hr_summary,
    )
    return jsonify(payload.model_dump())


def _normalize_day_key(raw_value: object) -> date:
    if isinstance(raw_value, datetime):
        return raw_value.date()
    if isinstance(raw_value, date):
        return raw_value
    if isinstance(raw_value, str):
        candidate = raw_value[:10]
        return date.fromisoformat(candidate)
    raise ValueError("Unsupported day key type")


def _build_trend_map(user_id: int, query: WearableTrendsQuery, start_date: date, end_date: date) -> Dict[date, Optional[float]]:
    day_start = _day_start_for(start_date)
    day_end = _day_start_for(end_date + timedelta(days=1))
    if query.metric in {"steps", "sleep"}:
        day_expr = func.date(WearableDailyAgg.day_start_utc).label("day")
        value_expr = (
            func.coalesce(func.sum(WearableDailyAgg.steps), 0).label("value")
            if query.metric == "steps"
            else func.coalesce(func.sum(WearableDailyAgg.sleep_seconds), 0).label("value")
        )
        rows = (
            db.session.query(day_expr, value_expr)
            .filter(
                WearableDailyAgg.user_id == user_id,
                WearableDailyAgg.day_start_utc >= day_start,
                WearableDailyAgg.day_start_utc < day_end,
            )
            .group_by(day_expr)
            .all()
        )
        if query.metric == "steps":
            return {_normalize_day_key(row[0]): float(row[1] or 0) for row in rows}
        return {_normalize_day_key(row[0]): float((row[1] or 0) / 60) for row in rows}
    day_expr = func.date(WearableCanonicalHR.timestamp_utc).label("day")
    rows = (
        db.session.query(day_expr, func.avg(WearableCanonicalHR.bpm).label("value"))
        .filter(
            WearableCanonicalHR.user_id == user_id,
            WearableCanonicalHR.timestamp_utc >= day_start,
            WearableCanonicalHR.timestamp_utc < day_end,
        )
        .group_by(day_expr)
        .all()
    )
    return {_normalize_day_key(row[0]): float(row[1]) for row in rows if row[1] is not None}


@wearable_read_bp.route("/wearable/trends", methods=["GET"])
@jwt_required()
def get_wearable_trends():
    user_id = _current_user_id()
    if user_id is None:
        return error_response("unauthorized", "Missing or invalid access token", 401)

    metric = request.args.get("metric")
    window = request.args.get("window")
    try:
        query = _validate_trends_query(metric, window)
    except ValidationError as exc:
        raise exc

    today = datetime.now(timezone.utc).date()
    start_date = today - timedelta(days=query.window - 1)
    value_map = _build_trend_map(user_id, query, start_date, today)

    points = []
    cursor = start_date
    numeric_values = []
    while cursor <= today:
        iso_date = cursor.isoformat()
        raw_value = value_map.get(cursor)
        if raw_value is None and query.metric in {"steps", "sleep"}:
            raw_value = 0.0
        if raw_value is not None:
            numeric_values.append(raw_value)
        points.append(WearableTrendPoint(date=iso_date, value=raw_value))
        cursor += timedelta(days=1)

    average = sum(numeric_values) / len(numeric_values) if numeric_values else None
    response = WearableTrendsResponse(
        metric=query.metric,
        window=query.window,
        average=average,
        values=points,
    )
    return jsonify(response.model_dump())
