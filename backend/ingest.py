from __future__ import annotations

from typing import Iterable, Sequence

import structlog
from extensions import db
from models import WearableRaw

logger = structlog.get_logger("wearable.ingest")


class WearableETLService:
    """Placeholder ETL service to process wearable raw rows."""

    def __init__(self, session, log=logger):
        self.session = session
        self.log = log

    def process_raw_rows(self, rows: Sequence[WearableRaw]) -> dict:
        processed = len(list(rows))
        return {"processed": processed, "skipped": 0, "errors": [], "aggregated": 0}

    def process_raw_by_ids(self, raw_ids: Sequence[int]) -> dict:
        rows = self.session.query(WearableRaw).filter(WearableRaw.id.in_(raw_ids)).all()
        return self.process_raw_rows(rows)


def process_wearable_raw_by_dedupe_keys(dedupe_keys: Sequence[str]) -> dict:
    keys = [key for key in dedupe_keys if key]
    if not keys:
        return {"processed": 0, "skipped": 0, "errors": [], "aggregated": 0}
    rows = db.session.query(WearableRaw).filter(WearableRaw.dedupe_key.in_(keys)).all()
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
