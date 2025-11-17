from __future__ import annotations

from datetime import date, datetime
from typing import Optional

import structlog
from extensions import db
from wearable_service import WearableAggregator

logger = structlog.get_logger("wearable.agg_jobs")


def rebuild_daily_aggregates_for_user(
    *,
    user_id: int,
    start_date: date,
    end_date: Optional[date] = None,
    source_id: Optional[int] = None,
) -> None:
    target_end = end_date or start_date
    aggregator = WearableAggregator(db.session, log=logger)
    aggregator.rebuild_range(
        user_id=user_id,
        start_date=start_date,
        end_date=target_end,
        source_id=source_id,
    )
    db.session.commit()


def rebuild_daily_aggregate_for_day(
    *,
    user_id: int,
    day: date,
    source_id: Optional[int] = None,
) -> None:
    rebuild_daily_aggregates_for_user(
        user_id=user_id,
        start_date=day,
        end_date=day,
        source_id=source_id,
    )
