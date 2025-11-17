"""Repository handling wearable device data integrations."""

from typing import Any, Dict, List, Optional

from db_utils import transactional_connection
from db_utils import connection as sa_connection
from extensions import db


def check_duplicate_records(
    source: str,
    data_type: str,
    start_time: str,
    end_time: str,
    user_id: int,
) -> List[dict]:
    """Fetch existing wearable records matching deduplication keys."""
    conn = sa_connection(db.engine)
    try:
        rows = conn.execute(
            """
            SELECT id, source, data_type, start_time, end_time
            FROM wearable_data
            WHERE source = ?
              AND data_type = ?
              AND start_time = ?
              AND end_time = ?
              AND user_id = ?
            """,
            (source, data_type, start_time, end_time, user_id),
        ).fetchall()
    finally:
        conn.close()
    return [dict(row) for row in rows]


def bulk_insert_wearable_data(records: List[Dict[str, Any]]) -> int:
    """Insert multiple wearable data records in a single transaction."""
    if not records:
        return 0

    with transactional_connection(db.engine) as conn:
        inserted = 0
        for record in records:
            conn.execute(
                """
                INSERT INTO wearable_data (
                    source,
                    data_type,
                    start_time,
                    end_time,
                    value,
                    unit,
                    user_id,
                    metadata,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record["source"],
                    record["data_type"],
                    record["start_time"],
                    record["end_time"],
                    record["value"],
                    record["unit"],
                    record["user_id"],
                    record.get("metadata"),
                    record.get("created_at"),
                ),
            )
            inserted += 1
    return inserted


def get_wearable_data_by_range(
    user_id: int,
    data_type: Optional[str],
    start_date: str,
    end_date: str,
    limit: int,
    offset: int,
) -> List[dict]:
    """Query wearable data within a date range with optional type filter."""
    conn = sa_connection(db.engine)
    try:
        params: List[Any] = [user_id, start_date, end_date]
        where_clause = "WHERE user_id = ? AND start_time >= ? AND end_time <= ?"
        if data_type:
            where_clause += " AND data_type = ?"
            params.append(data_type)
        params.extend([limit, offset])

        rows = conn.execute(
            f"""
            SELECT *
            FROM wearable_data
            {where_clause}
            ORDER BY start_time DESC
            LIMIT ? OFFSET ?
            """,
            params,
        ).fetchall()
    finally:
        conn.close()

    return [dict(row) for row in rows]


def get_wearable_data_summary(
    user_id: int,
    data_type: str,
    start_date: str,
    end_date: str,
) -> Optional[dict]:
    """Aggregate wearable data for a user in a date range."""
    conn = sa_connection(db.engine)
    try:
        row = conn.execute(
            """
            SELECT
                data_type,
                COUNT(*) AS count,
                SUM(value) AS total,
                AVG(value) AS average,
                MIN(value) AS min_value,
                MAX(value) AS max_value
            FROM wearable_data
            WHERE user_id = ?
              AND data_type = ?
              AND start_time >= ?
              AND end_time <= ?
            GROUP BY data_type
            """,
            (user_id, data_type, start_date, end_date),
        ).fetchone()
    finally:
        conn.close()

    return dict(row) if row else None


def delete_wearable_data_by_id(wearable_id: int, user_id: int) -> int:
    """Delete a wearable record by id scoped to a user."""
    with transactional_connection(db.engine) as conn:
        result = conn.execute(
            "DELETE FROM wearable_data WHERE id = ? AND user_id = ?",
            (wearable_id, user_id),
        )
        return result.rowcount


# --------------------------------------------------------------------------- raw ingest helpers
def get_wearable_source_by_dedupe(conn, dedupe_key: str) -> Optional[dict]:
    """Fetch a wearable source row by dedupe key using an existing connection."""
    row = conn.execute(
        "SELECT id FROM wearable_sources WHERE dedupe_key = ?",
        (dedupe_key,),
    ).fetchone()
    return dict(row) if row else None


def update_wearable_source(conn, source_id: int, updated_at: str, sync_metadata: str) -> int:
    """Update wearable source metadata timestamps using an existing connection."""
    result = conn.execute(
        "UPDATE wearable_sources SET updated_at = ?, sync_metadata = ? WHERE id = ?",
        (updated_at, sync_metadata, source_id),
    )
    return result.rowcount


def insert_wearable_source(
    conn,
    user_id: int,
    provider: str,
    external_id: str,
    display_name: str,
    sync_metadata: str,
    dedupe_key: str,
    now_iso: str,
) -> Optional[int]:
    """Insert a wearable source row and return its id."""
    result = conn.execute(
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
        (user_id, provider, external_id, display_name, sync_metadata, dedupe_key, now_iso, now_iso),
    )
    row = result.fetchone()
    return int(row["id"]) if row and "id" in row.keys() else None


def insert_wearable_raw(
    conn,
    user_id: int,
    source_id: int,
    collected_at_utc: str,
    received_at_utc: str,
    payload_json: str,
    dedupe_key: str,
    created_at: str,
) -> int:
    """Insert a wearable_raw record with deduplication handled via ON CONFLICT."""
    result = conn.execute(
        """
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
        """,
        (user_id, source_id, collected_at_utc, received_at_utc, payload_json, dedupe_key, created_at),
    )
    return result.rowcount
