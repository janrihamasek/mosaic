import io
from datetime import datetime, timedelta

import pytest


def test_get_entries_empty(client):
    response = client.get("/entries")
    assert response.status_code == 200
    assert response.get_json() == []


def test_add_activity_and_toggle(client):
    payload = {
        "name": "Reading",
        "category": "Leisure",
        "frequency_per_day": 2,
        "frequency_per_week": 5,
        "description": "Read a book",
    }
    response = client.post("/add_activity", json=payload)
    assert response.status_code == 201

    response = client.get("/activities")
    data = response.get_json()
    assert len(data) == 1
    activity_id = data[0]["id"]
    assert data[0]["active"] == 1
    assert data[0]["category"] == "Leisure"
    assert data[0]["goal"] == pytest.approx((2 * 5) / 7)
    assert data[0]["frequency_per_day"] == 2
    assert data[0]["frequency_per_week"] == 5
    assert data[0]["deactivated_at"] is None

    response = client.patch(f"/activities/{activity_id}/deactivate")
    assert response.status_code == 200

    response = client.get("/activities")
    assert response.get_json() == []

    response = client.get("/activities?all=true")
    data = response.get_json()
    assert len(data) == 1
    assert data[0]["active"] == 0
    assert data[0]["deactivated_at"] == datetime.now().strftime("%Y-%m-%d")


def test_add_activity_requires_category(client):
    resp = client.post("/add_activity", json={"name": "Yoga", "frequency_per_day": 1, "frequency_per_week": 3})
    assert resp.status_code == 400


def test_add_activity_requires_frequency(client):
    resp = client.post("/add_activity", json={"name": "Yoga", "category": "Health"})
    assert resp.status_code == 400
    resp = client.post("/add_activity", json={"name": "Yoga", "category": "Health", "frequency_per_day": 2})
    assert resp.status_code == 400
    resp = client.post("/add_activity", json={"name": "Yoga", "category": "Health", "frequency_per_week": 4})
    assert resp.status_code == 400


def test_add_entry_upsert(client):
    client.post(
        "/add_activity",
        json={
            "name": "Exercise",
            "category": "Health",
            "frequency_per_day": 3,
            "frequency_per_week": 7,
            "description": "Gym",
        },
    )
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
    assert data[0]["goal"] == pytest.approx((3 * 7) / 7)
    assert data[0]["goal"] == pytest.approx((3 * 7) / 7)


def test_today_and_finalize_day(client):
    client.post(
        "/add_activity",
        json={
            "name": "Coding",
            "category": "Work",
            "frequency_per_day": 1,
            "frequency_per_week": 4,
            "description": "Side project",
        },
    )
    client.post(
        "/add_activity",
        json={
            "name": "Workout",
            "category": "Health",
            "frequency_per_day": 2,
            "frequency_per_week": 6,
            "description": "Morning",
        },
    )

    target_date = "2024-02-20"
    response = client.get(f"/today?date={target_date}")
    today_data = response.get_json()
    assert len(today_data) == 2
    assert all("goal" in row for row in today_data)
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
        "date,activity,value,note,description,category,goal\n"
        "2024-03-01,Swim,2,,Morning swim,Fitness,12\n"
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
    assert activities[0]["goal"] == pytest.approx(12)


def test_update_activity_propagates(client):
    client.post(
        "/add_activity",
        json={
            "name": "Meditation",
            "category": "Mind",
            "frequency_per_day": 1,
            "frequency_per_week": 7,
            "description": "Morning calm",
        },
    )
    activity = client.get("/activities").get_json()[0]

    client.post(
        "/add_entry",
        json={"date": "2024-04-01", "activity": "Meditation", "value": 1, "note": ""},
    )

    update_payload = {
        "category": "Wellness",
        "frequency_per_day": 2,
        "frequency_per_week": 5,
        "description": "Updated desc",
    }
    resp = client.put(f"/activities/{activity['id']}", json=update_payload)
    assert resp.status_code == 200

    updated_activity = client.get("/activities").get_json()[0]
    assert updated_activity["category"] == "Wellness"
    assert updated_activity["goal"] == pytest.approx((2 * 5) / 7)
    assert updated_activity["frequency_per_day"] == 2
    assert updated_activity["frequency_per_week"] == 5

    entries = client.get("/entries").get_json()
    meditation_entry = next(e for e in entries if e["activity"] == "Meditation")
    assert meditation_entry["activity_description"] == "Updated desc"


def test_today_respects_deactivation_date(client):
    client.post(
        "/add_activity",
        json={
            "name": "Journal",
            "category": "Reflection",
            "frequency_per_day": 1,
            "frequency_per_week": 7,
            "description": "Daily journaling",
        },
    )
    activity = client.get("/activities").get_json()[0]
    activity_id = activity["id"]

    today = datetime.now()
    today_str = today.strftime("%Y-%m-%d")
    yesterday_str = (today - timedelta(days=1)).strftime("%Y-%m-%d")

    resp = client.get(f"/today?date={yesterday_str}")
    assert any(row["name"] == "Journal" for row in resp.get_json())

    client.patch(f"/activities/{activity_id}/deactivate")

    resp = client.get(f"/today?date={yesterday_str}")
    assert any(row["name"] == "Journal" for row in resp.get_json())

    resp = client.get(f"/today?date={today_str}")
    assert all(row["name"] != "Journal" for row in resp.get_json())


def test_entry_metadata_survives_activity_deletion(client):
    client.post(
        "/add_activity",
        json={
            "name": "Swim",
            "category": "Fitness",
            "frequency_per_day": 2,
            "frequency_per_week": 3,
            "description": "Pool laps",
        },
    )
    client.post(
        "/add_entry",
        json={"date": "2024-05-01", "activity": "Swim", "value": 1, "note": ""},
    )
    activity = client.get("/activities").get_json()[0]
    client.patch(f"/activities/{activity['id']}/deactivate")
    client.delete(f"/activities/{activity['id']}")

    entries = client.get("/entries").get_json()
    swim_entry = next(e for e in entries if e["activity"] == "Swim")
    assert swim_entry["category"] == "Fitness"
    assert swim_entry["activity_category"] == "Fitness"
    assert swim_entry["goal"] == pytest.approx((2 * 3) / 7)
    assert swim_entry["activity_goal"] == pytest.approx((2 * 3) / 7)


def test_entries_filtering(client):
    client.post(
        "/add_activity",
        json={
            "name": "Read",
            "category": "Leisure",
            "frequency_per_day": 1,
            "frequency_per_week": 7,
            "description": "Reading time",
        },
    )
    client.post(
        "/add_activity",
        json={
            "name": "Jog",
            "category": "Health",
            "frequency_per_day": 2,
            "frequency_per_week": 5,
            "description": "Jogging",
        },
    )

    client.post("/add_entry", json={"date": "2024-03-01", "activity": "Read", "value": 1, "note": ""})
    client.post("/add_entry", json={"date": "2024-03-05", "activity": "Read", "value": 1, "note": ""})
    client.post("/add_entry", json={"date": "2024-03-03", "activity": "Jog", "value": 2, "note": ""})

    resp = client.get("/entries?start_date=2024-03-02&end_date=2024-03-04")
    assert resp.status_code == 200
    filtered = resp.get_json()
    assert len(filtered) == 1
    assert filtered[0]["activity"] == "Jog"

    resp = client.get("/entries?activity=Read")
    assert resp.status_code == 200
    only_read = resp.get_json()
    assert {row["activity"] for row in only_read} == {"Read"}

    resp = client.get("/entries?category=Health")
    assert resp.status_code == 200
    health_entries = resp.get_json()
    assert all(row["category"] == "Health" for row in health_entries)


def test_stats_progress_activity_and_category(client):
    client.post(
        "/add_activity",
        json={
            "name": "Coding",
            "category": "Work",
            "frequency_per_day": 1,
            "frequency_per_week": 7,
            "description": "",
        },
    )
    client.post(
        "/add_activity",
        json={
            "name": "Run",
            "category": "Health",
            "frequency_per_day": 2,
            "frequency_per_week": 7,
            "description": "",
        },
    )

    entries = [
        ("2024-02-01", "Coding", 10),
        ("2024-02-10", "Coding", 10),
        ("2024-02-05", "Run", 15),
        ("2024-02-12", "Run", 25),
    ]
    for date, activity, value in entries:
        client.post(
            "/add_entry",
            json={"date": date, "activity": activity, "value": value, "note": ""},
        )

    activity_resp = client.get("/stats/progress?group=activity&period=30&date=2024-02-20")
    assert activity_resp.status_code == 200
    payload = activity_resp.get_json()
    assert payload["window"] == 30
    activity_stats = {row["name"]: row for row in payload["data"]}
    assert "Coding" in activity_stats and "Run" in activity_stats

    coding = activity_stats["Coding"]
    assert coding["total_value"] == pytest.approx(20.0)
    assert coding["total_goal"] == pytest.approx(30.0)
    assert coding["progress"] == pytest.approx(20.0 / 30.0)

    run_stats = activity_stats["Run"]
    assert run_stats["total_value"] == pytest.approx(40.0)
    assert run_stats["total_goal"] == pytest.approx(60.0)
    assert run_stats["progress"] == pytest.approx(40.0 / 60.0)

    category_resp = client.get(
        "/stats/progress?group=category&period=30&date=2024-02-20"
    )
    assert category_resp.status_code == 200
    category_payload = category_resp.get_json()
    categories = {row["name"]: row for row in category_payload["data"]}
    assert categories["Work"]["total_value"] == pytest.approx(20.0)
    assert categories["Work"]["total_goal"] == pytest.approx(30.0)
    assert categories["Work"]["progress"] == pytest.approx(20.0 / 30.0)
    assert categories["Health"]["total_value"] == pytest.approx(40.0)
    assert categories["Health"]["total_goal"] == pytest.approx(60.0)
    assert categories["Health"]["progress"] == pytest.approx(40.0 / 60.0)
