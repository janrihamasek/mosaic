"""
Wearable service.

Handles ingest of wearable batches and triggers downstream ETL while remaining
independent from HTTP concerns.
"""

import json
from datetime import datetime, timezone
from typing import Dict, List, Tuple
from zoneinfo import ZoneInfo

import structlog
from audit import log_event
from ingest import process_wearable_raw_by_dedupe_keys
from repositories import wearable_repo
from security import ValidationError, validate_wearable_batch_payload
from sqlalchemy.exc import SQLAlchemyError

from .common import db_transaction

logger = structlog.get_logger("mosaic.backend")


def _coerce_utc(dt_value: datetime, tzinfo: ZoneInfo) -> datetime:
    if dt_value.tzinfo is None:
        aware = dt_value.replace(tzinfo=tzinfo)
    else:
        aware = dt_value
    return aware.astimezone(timezone.utc)


def ingest_batch(user_id: int, payload: Dict) -> Tuple[Dict[str, object], int]:
    data = validate_wearable_batch_payload(payload or {})
    source_app = data["source_app"]
    device_id = data["device_id"]
    tz_name = data["tz"]
    tzinfo = ZoneInfo(tz_name)
    records = data["records"]

    accepted = 0
    duplicates = 0
    errors: List[dict] = []
    accepted_dedupes: List[str] = []
    now_iso = datetime.now(timezone.utc).isoformat()
    source_key = f"{user_id}:{source_app.lower()}:{device_id}"
    sync_metadata = json.dumps({"tz": tz_name})

    try:
        with db_transaction() as conn:
            source_row = wearable_repo.get_wearable_source_by_dedupe(conn, source_key)
            if source_row:
                source_id = source_row["id"]
                wearable_repo.update_wearable_source(
                    conn, source_id, now_iso, sync_metadata
                )
            else:
                source_id = wearable_repo.insert_wearable_source(
                    conn,
                    user_id,
                    source_app,
                    device_id,
                    source_app,
                    sync_metadata,
                    source_key,
                    now_iso,
                )

            if source_id is None:
                raise ValidationError(
                    "Unable to resolve wearable source",
                    code="internal_error",
                    status=500,
                )

            for index, record in enumerate(records):
                start_dt = record["start"]
                end_dt = record.get("end")
                try:
                    collected_utc = _coerce_utc(start_dt, tzinfo)
                    end_utc = _coerce_utc(end_dt, tzinfo) if end_dt else None
                    if end_utc and end_utc < collected_utc:
                        raise ValueError("end cannot be before start")
                except Exception as exc:
                    errors.append(
                        {
                            "index": index,
                            "dedupe_key": record["dedupe_key"],
                            "reason": str(exc),
                        }
                    )
                    continue

                record_payload = {
                    "type": record["type"],
                    "start": start_dt.isoformat(),
                    "end": end_dt.isoformat() if end_dt else None,
                    "fields": record["fields"],
                    "tz": tz_name,
                    "source_app": source_app,
                    "device_id": device_id,
                }
                try:
                    payload_json = json.dumps(record_payload)
                except (TypeError, ValueError) as exc:
                    errors.append(
                        {
                            "index": index,
                            "dedupe_key": record["dedupe_key"],
                            "reason": f"Invalid fields payload: {exc}",
                        }
                    )
                    continue

                inserted = wearable_repo.insert_wearable_raw(
                    conn,
                    user_id,
                    source_id,
                    collected_utc.isoformat(),
                    now_iso,
                    payload_json,
                    record["dedupe_key"],
                    now_iso,
                )
                if inserted:
                    accepted += 1
                    accepted_dedupes.append(record["dedupe_key"])
                else:
                    duplicates += 1
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
    try:
        etl_summary = process_wearable_raw_by_dedupe_keys(accepted_dedupes)
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("wearable.ingest.etl_failed", error=str(exc))
        errors.append({"reason": f"ETL failure: {exc}"})
        status_code = 500

    response_payload = {
        "accepted": accepted,
        "duplicates": duplicates,
        "errors": errors,
        "etl": etl_summary,
    }
    return response_payload, status_code
