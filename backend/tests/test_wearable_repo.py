from datetime import datetime, timezone

import pytest
from app import app
from extensions import db
from models import User, WearableRaw, WearableSource
from repositories import wearable_repo
from sqlalchemy import select


def _create_user(username: str = "wearable_user") -> User:
    user = User(username=username, password_hash="hash", created_at=datetime.utcnow())
    db.session.add(user)
    db.session.flush()
    return user


def _base_payload():
    return {
        "source_app": "Garmin",
        "device_id": "device-1",
        "tz": "UTC",
        "records": [
            {
                "type": "steps",
                "start": datetime(2024, 1, 1, tzinfo=timezone.utc),
                "end": None,
                "fields": {"steps": 10},
                "dedupe_key": "dedupe-1",
            }
        ],
    }


@pytest.mark.usefixtures("client")
def test_ingest_wearable_batch_creates_source_and_raw():
    with app.app_context():
        user = _create_user()
        payload = _base_payload()

        summary, status = wearable_repo.ingest_wearable_batch_atomically(
            user.id, payload
        )
        assert status == 201
        assert summary["accepted"] == 1
        assert summary["duplicates"] == 0
        assert summary["dedupes"] == ["dedupe-1"]

        src = db.session.execute(select(WearableSource)).scalar_one()
        assert src.dedupe_key == f"{user.id}:garmin:device-1"

        raw_row = db.session.execute(select(WearableRaw)).scalar_one()
        assert raw_row.dedupe_key == "dedupe-1"
        assert raw_row.user_id == user.id

        # duplicate ingest should not insert new rows
        summary2, status2 = wearable_repo.ingest_wearable_batch_atomically(
            user.id, payload
        )
        assert status2 == 200
        assert summary2["accepted"] == 0
        assert summary2["duplicates"] == 1
