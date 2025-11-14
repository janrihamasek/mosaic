from __future__ import annotations

from typing import Iterable, Sequence

import structlog

from extensions import db
from models import WearableRaw
from wearable_service import WearableETLService

logger = structlog.get_logger("wearable.ingest")


def process_wearable_raw_by_dedupe_keys(dedupe_keys: Sequence[str]) -> dict:
    keys = [key for key in dedupe_keys if key]
    if not keys:
        return {"processed": 0, "skipped": 0, "errors": [], "aggregated": 0}
    rows = (
        db.session.query(WearableRaw)
        .filter(WearableRaw.dedupe_key.in_(keys))
        .all()
    )
    service = WearableETLService(db.session, log=logger)
    result = service.process_raw_rows(rows)
    db.session.commit()
    return result


def process_wearable_raw_by_ids(raw_ids: Iterable[int]) -> dict:
    ids = [rid for rid in raw_ids if rid]
    if not ids:
        return {"processed": 0, "skipped": 0, "errors": [], "aggregated": 0}
    service = WearableETLService(db.session, log=logger)
    result = service.process_raw_by_ids(ids)
    db.session.commit()
    return result
