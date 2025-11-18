from datetime import datetime, timezone

import pytest
from services import wearable_service
from repositories import wearable_repo


def _payload():
    return {
        "source_app": "Fitbit",
        "device_id": "dev-1",
        "tz": "UTC",
        "records": [
            {
                "type": "hr",
                "start": datetime(2024, 1, 1, tzinfo=timezone.utc),
                "end": None,
                "fields": {"bpm": 70},
                "dedupe_key": "d1",
            }
        ],
    }


def test_ingest_batch_calls_repo_and_etl(monkeypatch):
    def fake_ingest(user_id, payload):
        assert payload["source_app"] == "Fitbit"
        return {"accepted": 1, "duplicates": 0, "errors": [], "dedupes": ["d1"]}, 201

    etl_calls = {}

    def fake_process(keys):
        etl_calls["keys"] = keys
        return {"processed": len(keys), "skipped": 0, "errors": [], "aggregated": 0}

    monkeypatch.setattr(wearable_repo, "ingest_wearable_batch_atomically", fake_ingest)
    monkeypatch.setattr(
        "services.wearable_service.process_wearable_raw_by_dedupe_keys", fake_process
    )

    payload = _payload()
    response, status = wearable_service.ingest_batch(1, payload)

    assert status == 201
    assert response["accepted"] == 1
    assert response["etl"]["processed"] == 1
    assert etl_calls["keys"] == ["d1"]
