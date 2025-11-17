"""
Wearable service.

Handles ingest of wearable batches and triggers downstream ETL while remaining
independent from HTTP concerns.
"""

import json
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from typing import Dict, List, Tuple

import structlog
from sqlalchemy.exc import SQLAlchemyError

from audit import log_event
from ingest import process_wearable_raw_by_dedupe_keys
from security import ValidationError, validate_wearable_batch_payload
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
            source_row = conn.execute(
                "SELECT id FROM wearable_sources WHERE dedupe_key = ?",
                (source_key,),
            ).fetchone()
            if source_row:
                source_id = source_row["id"]
                conn.execute(
                    "UPDATE wearable_sources SET updated_at = ?, sync_metadata = ? WHERE id = ?",
                    (now_iso, sync_metadata, source_id),
                )
            else:
                insert_result = conn.execute(
                    """
                    INSERT INTO wearable_sources (
                        user_id,
                        provider,
                        external_id,
                        display_name,
                        sync_metadata,
                        last_synced_at,
                        dedupe_key,
                        created_at,
                        updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, NULL, ?, ?, ?)
                    RETURNING id
                    """,
                    (
                        user_id,
                        source_app,
                        device_id,
                        source_app,
                        sync_metadata,
                        source_key,
                        now_iso,
                        now_iso,
                    ),
                )
                new_row = insert_result.fetchone()
                source_id = new_row["id"] if new_row else None

            if source_id is None:
                raise ValidationError("Unable to resolve wearable source", code="internal_error", status=500)

            insert_sql = """
                INSERT INTO wearable_raw (
                    user_id,
                    source_id,
                    collected_at_utc,
                    received_at_utc,
                    payload,
                    dedupe_key,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (dedupe_key) DO NOTHING
            """

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

                result = conn.execute(
                    insert_sql,
                    (
                        user_id,
                        source_id,
                        collected_utc.isoformat(),
                        now_iso,
                        payload_json,
                        record["dedupe_key"],
                        now_iso,
                    ),
                )
                if result.rowcount:
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
