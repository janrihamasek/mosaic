import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app import app
from extensions import db
from models import (
    User,
    WearableCanonicalHR,
    WearableCanonicalSleepSession,
    WearableDailyAgg,
)


PASSWORD = "StrongPass123"


def _register_and_login(client, username):
    client.post("/register", json={"username": username, "password": PASSWORD})
    login = client.post("/login", json={"username": username, "password": PASSWORD})
    assert login.status_code == 200
    token = login.get_json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    with app.app_context():
        user = db.session.query(User).filter_by(username=username).one()
    return headers, user.id


def _insert_daily_agg(user_id: int, date_value: datetime.date, steps: int, resting: int, sleep_seconds: int):
    day_start = datetime(date_value.year, date_value.month, date_value.day, tzinfo=timezone.utc)
    agg = WearableDailyAgg(
        user_id=user_id,
        day_start_utc=day_start,
        steps=steps,
        resting_heart_rate=resting,
        sleep_seconds=sleep_seconds,
        dedupe_key=f"{user_id}:main:{date_value.isoformat()}",
    )
    db.session.add(agg)


def _insert_sleep_session(user_id: int, start: datetime, duration: int, score: int):
    session = WearableCanonicalSleepSession(
        user_id=user_id,
        start_time_utc=start,
        end_time_utc=start + timedelta(seconds=duration),
        duration_seconds=duration,
        score=score,
        dedupe_key=str(uuid.uuid4()),
    )
    db.session.add(session)


def _insert_hr_sample(user_id: int, timestamp: datetime, bpm: int):
    sample = WearableCanonicalHR(
        user_id=user_id,
        timestamp_utc=timestamp,
        bpm=bpm,
        dedupe_key=str(uuid.uuid4()),
    )
    db.session.add(sample)


def test_wearable_day_requires_auth(client):
    response = client.get("/wearable/day")
    assert response.status_code == 401
    assert response.get_json()["error"]["code"] == "unauthorized"


def test_wearable_day_returns_user_data(client):
    headers, user_id = _register_and_login(client, "wearable_user")
    other_headers, other_user_id = _register_and_login(client, "other_user")

    today = datetime.now(timezone.utc).date()
    earlier = today - timedelta(days=1)

    with app.app_context():
        _insert_daily_agg(user_id, today, steps=1500, resting=58, sleep_seconds=3600)
        _insert_daily_agg(user_id, earlier, steps=900, resting=60, sleep_seconds=1800)
        _insert_daily_agg(other_user_id, today, steps=9999, resting=45, sleep_seconds=7200)
        _insert_sleep_session(user_id, datetime.combine(today, datetime.min.time(), tzinfo=timezone.utc), 3600, 84)
        _insert_hr_sample(user_id, datetime.combine(today, datetime.min.time(), tzinfo=timezone.utc) + timedelta(hours=8), 70)
        _insert_hr_sample(user_id, datetime.combine(today, datetime.min.time(), tzinfo=timezone.utc) + timedelta(hours=12), 90)
        db.session.commit()

    response = client.get("/wearable/day", headers=headers)
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["steps"] == 1500
    assert payload["sleep"]["total_min"] == 60.0
    assert payload["sleep"]["sessions"] == 1
    assert payload["sleep"]["efficiency"] == 84.0
    assert payload["hr"]["rest"] == 58
    assert payload["hr"]["min"] == 70
    assert payload["hr"]["max"] == 90
    assert round(payload["hr"]["avg"], 2) == 80.0


def test_wearable_trends_returns_windowed_data(client):
    headers, user_id = _register_and_login(client, "trend_user")
    today = datetime.now(timezone.utc).date()
    previous = today - timedelta(days=1)

    with app.app_context():
        _insert_daily_agg(user_id, today, steps=2000, resting=55, sleep_seconds=2400)
        _insert_daily_agg(user_id, previous, steps=800, resting=57, sleep_seconds=1200)
        _insert_hr_sample(user_id, datetime.combine(today, datetime.min.time(), tzinfo=timezone.utc) + timedelta(hours=4), 66)
        _insert_hr_sample(user_id, datetime.combine(previous, datetime.min.time(), tzinfo=timezone.utc) + timedelta(hours=4), 72)
        db.session.commit()

    response = client.get("/wearable/trends?metric=steps&window=7", headers=headers)
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["metric"] == "steps"
    assert payload["window"] == 7
    assert len(payload["values"]) == 7
    assert payload["values"][-1]["value"] == 2000.0
    assert payload["values"][-2]["value"] == 800.0
    assert payload["average"] == pytest.approx(sum(v["value"] for v in payload["values"]) / 7)


def test_wearable_trends_requires_auth(client):
    response = client.get("/wearable/trends?metric=steps&window=7")
    assert response.status_code == 401
    assert response.get_json()["error"]["code"] == "unauthorized"
