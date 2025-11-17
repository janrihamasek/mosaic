import time
import uuid

import jwt
import pytest
from app import app, cache_get, cache_set, invalidate_cache


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
