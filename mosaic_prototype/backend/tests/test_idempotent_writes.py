import uuid


def _auth_headers(client):
    username = f"idempotent_{uuid.uuid4().hex[:8]}"
    password = "Passw0rd!"
    register = client.post("/register", json={"username": username, "password": password})
    assert register.status_code == 201
    login = client.post("/login", json={"username": username, "password": password})
    assert login.status_code == 200
    tokens = login.get_json()
    return {
        "Authorization": f"Bearer {tokens['access_token']}",
        "X-CSRF-Token": tokens["csrf_token"],
    }


def test_add_entry_idempotent(client):
    headers = _auth_headers(client)
    payload = {"date": "2025-11-08", "activity": "Test Entry", "value": 1.5, "note": "local"}
    key = "entry-key-001"

    first = client.post("/add_entry", json=payload, headers={**headers, "X-Idempotency-Key": key})
    assert first.status_code in (200, 201)

    second = client.post("/add_entry", json=payload, headers={**headers, "X-Idempotency-Key": key})
    assert second.status_code == first.status_code
    assert second.get_json()["message"]

    today = client.get("/today", query_string={"date": payload["date"]}, headers=headers)
    assert today.status_code == 200
    rows = today.get_json()
    matching = [row for row in rows if row["name"] == payload["activity"]]
    assert len(matching) == 1
    assert float(matching[0]["value"]) == payload["value"]


def test_add_activity_idempotent_and_overwrite(client):
    headers = _auth_headers(client)
    payload = {
        "name": "Offline Habit",
        "category": "Offline",
        "goal": 1.0,
        "description": "initial",
        "frequency_per_day": 1,
        "frequency_per_week": 7,
    }
    key = "activity-key-001"

    first = client.post("/add_activity", json=payload, headers={**headers, "X-Idempotency-Key": key})
    assert first.status_code == 201

    replay = client.post("/add_activity", json=payload, headers={**headers, "X-Idempotency-Key": key})
    assert replay.status_code == 201

    overwrite_payload = {
        **payload,
        "goal": 2.5,
        "description": "overwrite",
    }
    overwrite = client.post(
        "/add_activity",
        json=overwrite_payload,
        headers={**headers, "X-Overwrite-Existing": "1"},
    )
    assert overwrite.status_code == 200
    data = overwrite.get_json()
    assert data["message"] == "Kategorie aktualizována"

    activities = client.get("/activities?all=true", headers=headers)
    assert activities.status_code == 200
    items = activities.get_json()
    target = next(item for item in items if item["name"] == payload["name"])
    assert float(target["goal"]) == overwrite_payload["goal"]
    assert target["description"] == overwrite_payload["description"]
