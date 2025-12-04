import time
import uuid

import jwt
import pytest
from app import app
from extensions import db
from infra.cache_manager import cache_get, cache_set, invalidate_cache
from sqlalchemy import text


def test_register_and_login_flow(client):
    username = f"user_{uuid.uuid4().hex[:6]}"
    password = "StrongPass123"

    register = client.post(
        "/register", json={"username": username, "password": password}
    )
    assert register.status_code == 201

    login = client.post("/login", json={"username": username, "password": password})
    assert login.status_code == 200
    payload = login.get_json()
    assert {"access_token", "csrf_token", "token_type", "expires_in"} <= payload.keys()

    # use issued token to access a protected endpoint
    resp = client.get(
        "/entries",
        headers={
            "Authorization": f"Bearer {payload['access_token']}",
            "X-CSRF-Token": payload["csrf_token"],
        },
    )
    assert resp.status_code == 200


def test_login_invalid_credentials(client):
    username = f"user_{uuid.uuid4().hex[:6]}"
    client.post("/register", json={"username": username, "password": "ValidPass123"})

    bad_login = client.post("/login", json={"username": username, "password": "wrong"})
    assert bad_login.status_code == 401
    body = bad_login.get_json()
    assert body["error"]["code"] == "invalid_credentials"


def test_invalid_token_rejected(client):
    resp = client.get(
        "/entries",
        headers={
            "Authorization": "Bearer invalid-token",
            "X-CSRF-Token": "whatever",
        },
    )
    assert resp.status_code == 401
    assert resp.get_json()["error"]["code"] == "unauthorized"


def test_expired_token_rejected(client, monkeypatch):
    username = f"user_{uuid.uuid4().hex[:6]}"
    password = "StrongPass123"
    client.post("/register", json={"username": username, "password": password})
    login = client.post("/login", json={"username": username, "password": password})
    token = login.get_json()["access_token"]

    # decode & re-encode token with past expiry to simulate expiration
    decoded = jwt.decode(
        token, app.config["JWT_SECRET"], algorithms=[app.config["JWT_ALGORITHM"]]
    )
    decoded["exp"] = 0
    expired_token = jwt.encode(
        decoded, app.config["JWT_SECRET"], algorithm=app.config["JWT_ALGORITHM"]
    )

    resp = client.get(
        "/entries",
        headers={
            "Authorization": f"Bearer {expired_token}",
            "X-CSRF-Token": login.get_json()["csrf_token"],
        },
    )
    assert resp.status_code == 401
    assert resp.get_json()["error"]["code"] == "token_expired"


def test_cache_helpers(monkeypatch):
    key = ("cache",)
    cache_set("unit", key, {"value": 1}, ttl=5)
    cached = cache_get("unit", key)
    assert cached == {"value": 1}

    # expire by advancing time
    original_time = time.time
    monkeypatch.setattr("app.time", lambda: original_time() + 10)
    assert cache_get("unit", key) is None

    # store and invalidate
    monkeypatch.setattr("app.time", original_time)
    cache_set("unit", key, {"value": 2}, ttl=5)
    invalidate_cache("unit")
    assert cache_get("unit", key) is None


def _create_user_and_login(client, username: str, password: str):
    register = client.post("/register", json={"username": username, "password": password})
    assert register.status_code == 201
    login = client.post("/login", json={"username": username, "password": password})
    assert login.status_code == 200
    tokens = login.get_json()
    headers = {
        "Authorization": f"Bearer {tokens['access_token']}",
        "X-CSRF-Token": tokens["csrf_token"],
    }
    return headers


def test_wipe_user_data_requires_auth(client):
    response = client.delete("/user/data")
    assert response.status_code == 401
    body = response.get_json()
    assert body["error"]["code"] == "unauthorized"


def test_wipe_user_data_affects_only_current_user(client):
    password = "StrongPass123"
    headers_user1 = _create_user_and_login(client, f"user_{uuid.uuid4().hex[:6]}", password)
    headers_user2 = _create_user_and_login(client, f"user_{uuid.uuid4().hex[:6]}", password)

    profile_resp = client.get("/user", headers=headers_user1)
    assert profile_resp.status_code == 200
    user1_id = profile_resp.get_json()["id"]

    # Seed data for both users
    client.post(
        "/add_activity",
        json={
            "name": "Run",
            "category": "Fitness",
            "frequency_per_day": 1,
            "frequency_per_week": 3,
        },
        headers=headers_user1,
    )
    client.post(
        "/add_entry",
        json={"date": "2024-05-01", "activity": "Run", "value": 5, "note": "ok"},
        headers=headers_user1,
    )
    client.post(
        "/backup/toggle",
        json={"enabled": True, "interval_minutes": 30},
        headers=headers_user1,
    )

    client.post(
        "/add_activity",
        json={
            "name": "Swim",
            "category": "Health",
            "frequency_per_day": 1,
            "frequency_per_week": 2,
        },
        headers=headers_user2,
    )
    client.post(
        "/add_entry",
        json={"date": "2024-05-02", "activity": "Swim", "value": 2, "note": "pool"},
        headers=headers_user2,
    )

    response = client.delete("/user/data", headers=headers_user1)
    assert response.status_code == 200
    assert response.get_json()["message"]

    entries_user1 = client.get("/entries", headers=headers_user1)
    assert entries_user1.status_code == 200
    assert entries_user1.get_json() == []

    activities_user1 = client.get("/activities", headers=headers_user1)
    assert activities_user1.status_code == 200
    assert [a for a in activities_user1.get_json() if not a.get("is_system")] == []

    entries_user2 = client.get("/entries", headers=headers_user2)
    assert entries_user2.status_code == 200
    assert len(entries_user2.get_json()) == 1

    activities_user2 = client.get("/activities", headers=headers_user2)
    assert activities_user2.status_code == 200
    non_system_user2 = [a for a in activities_user2.get_json() if not a.get("is_system")]
    assert len(non_system_user2) == 1

    with app.app_context():
        count = db.session.execute(
            text("SELECT COUNT(1) FROM backup_settings WHERE user_id = :uid"),
            {"uid": user1_id},
        ).scalar()
    assert count == 0
