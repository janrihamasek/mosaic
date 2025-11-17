"""
Wearable service.

Handles ingest of wearable batches and triggers downstream ETL while remaining
independent from HTTP concerns.
"""

import json
from datetime import datetime, timezone
from typing import Dict, List, Tuple

import structlog
from repositories import wearable_repo
from security import ValidationError, validate_wearable_batch_payload
from sqlalchemy.exc import SQLAlchemyError

logger = structlog.get_logger("mosaic.backend")


def ingest_batch(user_id: int, payload: Dict) -> Tuple[Dict[str, object], int]:
    data = validate_wearable_batch_payload(payload or {})
    source_app = data["source_app"]
    device_id = data["device_id"]
    tz_name = data["tz"]
    records = data["records"]

    errors: List[dict] = []
    now_iso = datetime.now(timezone.utc).isoformat()
    source_key = f"{user_id}:{source_app.lower()}:{device_id}"
    sync_metadata = json.dumps({"tz": tz_name})
    batch_context = {
        "source_app": source_app,
        "device_id": device_id,
        "tz": tz_name,
        "now_iso": now_iso,
        "sync_metadata": sync_metadata,
        "source_key": source_key,
    }
    records_with_context = [dict(record, _batch_context=batch_context) for record in records]

    try:
        accepted, duplicates = wearable_repo.process_wearable_batch(
            records_with_context, user_id
        )
    except SQLAlchemyError as exc:
        raise ValidationError(str(exc), code="database_error", status=500)

    logger.bind(
        user_id=user_id,
        source_app=source_app,
        device_id=device_id,
        records=len(records),
        accepted=accepted,
        duplicates=duplicates,
        errors=len(errors),
    ).info("wearable.ingest_batch")

    status_code = 201 if accepted > 0 else 200
    etl_summary = {"processed": 0, "skipped": 0, "errors": [], "aggregated": 0}

    response_payload = {
        "accepted": accepted,
        "duplicates": duplicates,
        "errors": errors,
        "etl": etl_summary,
    }
    return response_payload, status_code
