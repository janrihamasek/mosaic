from __future__ import annotations

from datetime import datetime
from typing import Optional

from flask import Blueprint, jsonify, request
from sqlalchemy import desc

from audit import get_runtime_logs
from models import ActivityLog
from security import error_response, require_admin

logs_bp = Blueprint("logs", __name__, url_prefix="/logs")


def _parse_iso_timestamp(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _parse_positive_int(value: Optional[str], *, default: int, minimum: int = 1, maximum: int = 500) -> int:
    try:
        parsed = int(value) if value is not None else default
    except (TypeError, ValueError):
        raise ValueError
    if parsed < minimum:
        raise ValueError
    return min(parsed, maximum)


@logs_bp.get("/activity")
@require_admin
def list_activity_logs():
    try:
        limit = _parse_positive_int(request.args.get("limit"), default=100, minimum=1, maximum=500)
        offset = _parse_positive_int(request.args.get("offset"), default=0, minimum=0, maximum=10_000)
    except ValueError:
        return error_response("invalid_query", "Invalid pagination parameters", 400)

    user_id = request.args.get("user_id", type=int)
    event_type = request.args.get("event_type")
    level = request.args.get("level")
    start_ts = _parse_iso_timestamp(request.args.get("start"))
    end_ts = _parse_iso_timestamp(request.args.get("end"))
    if request.args.get("start") and not start_ts:
        return error_response("invalid_query", "Invalid start timestamp", 400)
    if request.args.get("end") and not end_ts:
        return error_response("invalid_query", "Invalid end timestamp", 400)

    query = ActivityLog.query
    if user_id is not None:
        query = query.filter(ActivityLog.user_id == user_id)
    if event_type:
        query = query.filter(ActivityLog.event_type == event_type)
    if level:
        query = query.filter(ActivityLog.level == level.lower())
    if start_ts:
        query = query.filter(ActivityLog.timestamp >= start_ts)
    if end_ts:
        query = query.filter(ActivityLog.timestamp <= end_ts)

    total = query.count()
    rows = (
        query.order_by(desc(ActivityLog.timestamp))
        .offset(offset)
        .limit(limit)
        .all()
    )

    return jsonify(
        {
            "items": [row.to_dict() for row in rows],
            "limit": limit,
            "offset": offset,
            "total": total,
        }
    )


@logs_bp.get("/runtime")
@require_admin
def runtime_logs():
    limit = request.args.get("limit", type=int)
    logs = get_runtime_logs(limit)
    return jsonify({"logs": logs, "limit": limit or len(logs)})
