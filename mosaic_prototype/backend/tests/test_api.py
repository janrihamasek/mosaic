import io


def test_get_entries_empty(client):
    response = client.get("/entries")
    assert response.status_code == 200
    assert response.get_json() == []


def test_add_activity_and_toggle(client):
    payload = {"name": "Reading", "category": "Leisure", "description": "Read a book"}
    response = client.post("/add_activity", json=payload)
    assert response.status_code == 201

    response = client.get("/activities")
    data = response.get_json()
    assert len(data) == 1
    activity_id = data[0]["id"]
    assert data[0]["active"] == 1
    assert data[0]["category"] == "Leisure"

    response = client.patch(f"/activities/{activity_id}/deactivate")
    assert response.status_code == 200

    response = client.get("/activities")
    assert response.get_json() == []

    response = client.get("/activities?all=true")
    data = response.get_json()
    assert len(data) == 1
    assert data[0]["active"] == 0


def test_add_activity_requires_category(client):
    resp = client.post("/add_activity", json={"name": "Yoga"})
    assert resp.status_code == 400


def test_add_entry_upsert(client):
    client.post("/add_activity", json={"name": "Exercise", "category": "Health", "description": "Gym"})
    date_str = "2024-01-15"

    response = client.post(
        "/add_entry",
        json={"date": date_str, "activity": "Exercise", "value": 3, "note": "First"},
    )
    assert response.status_code == 201

    response = client.post(
        "/add_entry",
        json={"date": date_str, "activity": "Exercise", "value": 4, "note": "Updated"},
    )
    assert response.status_code == 200

    response = client.get("/entries")
    data = response.get_json()
    assert len(data) == 1
    assert data[0]["note"] == "Updated"
    assert float(data[0]["value"]) == 4
    assert data[0]["category"] == "Health"


def test_today_and_finalize_day(client):
    client.post("/add_activity", json={"name": "Coding", "category": "Work", "description": "Side project"})
    client.post("/add_activity", json={"name": "Workout", "category": "Health", "description": "Morning"})

    target_date = "2024-02-20"
    response = client.get(f"/today?date={target_date}")
    today_data = response.get_json()
    assert len(today_data) == 2
    assert {row["category"] for row in today_data} == {"Work", "Health"}

    response = client.post("/finalize_day", json={"date": target_date})
    assert response.status_code == 200

    response = client.get("/entries")
    entries = [e for e in response.get_json() if e["date"] == target_date]
    assert len(entries) == 2
    assert all(float(e["value"]) == 0 for e in entries)

    # ensure finalize_day is idempotent
    response = client.post("/finalize_day", json={"date": target_date})
    assert response.status_code == 200
    response = client.get("/entries")
    entries = [e for e in response.get_json() if e["date"] == target_date]
    assert len(entries) == 2


def test_add_entry_validation(client):
    response = client.post("/add_entry", json={"activity": "", "date": "2024-15-01"})
    assert response.status_code == 400
    assert "error" in response.get_json()

    long_note = "a" * 120
    response = client.post(
        "/add_entry",
        json={"activity": "Run", "date": "2024-01-01", "value": "abc", "note": long_note},
    )
    assert response.status_code == 400


def test_rate_limit_enforced(client):
    from app import app

    original = app.config["RATE_LIMITS"]["add_entry"]
    app.config["RATE_LIMITS"]["add_entry"] = {"limit": 2, "window": 60}

    try:
        payload = {"date": "2024-01-01", "activity": "Test", "value": 1}
        r1 = client.post("/add_entry", json=payload)
        assert r1.status_code in (200, 201)
        r2 = client.post("/add_entry", json=payload)
        assert r2.status_code in (200, 201)
        r3 = client.post("/add_entry", json=payload)
        assert r3.status_code == 429
    finally:
        app.config["RATE_LIMITS"]["add_entry"] = original


def test_api_key_enforced(client):
    from app import app

    app.config["API_KEY"] = "secret"
    try:
        resp = client.get("/entries")
        assert resp.status_code == 401

        resp = client.get("/entries", headers={"X-API-Key": "secret"})
        assert resp.status_code == 200
    finally:
        app.config["API_KEY"] = None


def test_import_csv_endpoint(client):
    csv_data = (
        "date,activity,value,note,description,category\n"
        "2024-03-01,Swim,2,,Morning swim,Fitness\n"
    )
    data = {
        "file": (io.BytesIO(csv_data.encode("utf-8")), "activities.csv"),
    }
    response = client.post("/import_csv", data=data, content_type="multipart/form-data")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["summary"]["created"] == 1

    # CSV import should have created an activity with category
    activities = client.get("/activities").get_json()
    assert activities[0]["category"] == "Fitness"
