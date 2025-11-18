"""
Wearable service.

Handles ingest of wearable batches and triggers downstream ETL while remaining
independent from HTTP concerns.
"""

from datetime import datetime, timezone
from typing import Dict, List, Tuple

import structlog
from ingest import process_wearable_raw_by_dedupe_keys
from repositories import wearable_repo
from security import ValidationError, validate_wearable_batch_payload
from sqlalchemy.exc import SQLAlchemyError

logger = structlog.get_logger("mosaic.backend")


def ingest_batch(user_id: int, payload: Dict) -> Tuple[Dict[str, object], int]:
    data = validate_wearable_batch_payload(payload or {})

    try:
        summary, status_code = wearable_repo.ingest_wearable_batch_atomically(
            user_id, data
        )
    except SQLAlchemyError as exc:
        raise ValidationError(str(exc), code="database_error", status=500)

    etl_summary = {"processed": 0, "skipped": 0, "errors": [], "aggregated": 0}
    if summary.get("dedupes"):
        try:
            etl_summary = process_wearable_raw_by_dedupe_keys(summary["dedupes"])
        except Exception as exc:  # pragma: no cover - defensive
            logger.bind(user_id=user_id, error=str(exc)).error(
                "wearable.etl_failed", exc_info=True
            )

    logger.bind(
        user_id=user_id,
        source_app=data["source_app"],
        device_id=data["device_id"],
        records=len(data.get("records") or []),
        accepted=summary.get("accepted", 0),
        duplicates=summary.get("duplicates", 0),
        errors=len(summary.get("errors") or []),
    ).info("wearable.ingest_batch")

    response_payload = {
        "accepted": summary.get("accepted", 0),
        "duplicates": summary.get("duplicates", 0),
        "errors": summary.get("errors") or [],
        "etl": etl_summary,
    }
    return response_payload, status_code
