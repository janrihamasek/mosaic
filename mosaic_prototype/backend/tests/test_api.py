import io
import uuid
from datetime import datetime, timedelta

import pytest


@pytest.fixture
def auth_headers(client):
    username = f"user_{uuid.uuid4().hex[:8]}"
    password = "Passw0rd!"
    register_resp = client.post("/register", json={"username": username, "password": password})
    assert register_resp.status_code == 201
    login_resp = client.post("/login", json={"username": username, "password": password})
    assert login_resp.status_code == 200
    tokens = login_resp.get_json()
    return {
        "Authorization": f"Bearer {tokens['access_token']}",
        "X-CSRF-Token": tokens["csrf_token"],
    }


def test_get_entries_empty(client, auth_headers):
    response = client.get("/entries", headers=auth_headers)
    assert response.status_code == 200
    assert response.get_json() == []


def test_add_activity_and_toggle(client, auth_headers):
    payload = {
        "name": "Reading",
        "category": "Leisure",
        "frequency_per_day": 2,
        "frequency_per_week": 5,
        "description": "Read a book",
    }
    response = client.post("/add_activity", json=payload, headers=auth_headers)
    assert response.status_code == 201

    response = client.get("/activities", headers=auth_headers)
    data = response.get_json()
    assert len(data) == 1
    activity_id = data[0]["id"]
    assert data[0]["active"] == 1
    assert data[0]["category"] == "Leisure"
    assert data[0]["goal"] == pytest.approx((2 * 5) / 7)
    assert data[0]["frequency_per_day"] == 2
    assert data[0]["frequency_per_week"] == 5
    assert data[0]["deactivated_at"] is None

    response = client.patch(f"/activities/{activity_id}/deactivate", headers=auth_headers)
    assert response.status_code == 200

    response = client.get("/activities", headers=auth_headers)
    assert response.get_json() == []

    response = client.get("/activities?all=true", headers=auth_headers)
    data = response.get_json()
    assert len(data) == 1
    assert data[0]["active"] == 0
    assert data[0]["deactivated_at"] == datetime.now().strftime("%Y-%m-%d")


def test_add_activity_requires_category(client, auth_headers):
    resp = client.post(
        "/add_activity",
        json={"name": "Yoga", "frequency_per_day": 1, "frequency_per_week": 3},
        headers=auth_headers,
    )
    assert resp.status_code == 400
    body = resp.get_json()
    assert body["error"]["code"] == "invalid_input"
    assert body["error"]["message"]


def test_add_activity_requires_frequency(client, auth_headers):
    resp = client.post("/add_activity", json={"name": "Yoga", "category": "Health"}, headers=auth_headers)
    assert resp.status_code == 400
    assert resp.get_json()["error"]["code"] == "invalid_input"
    resp = client.post(
        "/add_activity",
        json={"name": "Yoga", "category": "Health", "frequency_per_day": 2},
        headers=auth_headers,
    )
    assert resp.status_code == 400
    assert resp.get_json()["error"]["code"] == "invalid_input"
    resp = client.post(
        "/add_activity",
        json={"name": "Yoga", "category": "Health", "frequency_per_week": 4},
        headers=auth_headers,
    )
    assert resp.status_code == 400
    assert resp.get_json()["error"]["code"] == "invalid_input"


def test_add_entry_upsert(client, auth_headers):
    client.post(
        "/add_activity",
        json={
            "name": "Exercise",
            "category": "Health",
            "frequency_per_day": 3,
            "frequency_per_week": 7,
            "description": "Gym",
        },
        headers=auth_headers,
    )
    date_str = "2024-01-15"

    response = client.post(
        "/add_entry",
        json={"date": date_str, "activity": "Exercise", "value": 3, "note": "First"},
        headers=auth_headers,
    )
    assert response.status_code == 201

    response = client.post(
        "/add_entry",
        json={"date": date_str, "activity": "Exercise", "value": 4, "note": "Updated"},
        headers=auth_headers,
    )
    assert response.status_code == 200

    response = client.get("/entries", headers=auth_headers)
    data = response.get_json()
    assert len(data) == 1
    assert data[0]["note"] == "Updated"
    assert float(data[0]["value"]) == 4
    assert data[0]["category"] == "Health"
    assert data[0]["goal"] == pytest.approx((3 * 7) / 7)
    assert data[0]["goal"] == pytest.approx((3 * 7) / 7)


def test_today_and_finalize_day(client, auth_headers):
    client.post(
        "/add_activity",
        json={
            "name": "Coding",
            "category": "Work",
            "frequency_per_day": 1,
            "frequency_per_week": 4,
            "description": "Side project",
        },
        headers=auth_headers,
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
        headers=auth_headers,
    )

    target_date = "2024-02-20"
    response = client.get(f"/today?date={target_date}", headers=auth_headers)
    today_data = response.get_json()
    assert len(today_data) == 2
    assert all("goal" in row for row in today_data)
    assert {row["category"] for row in today_data} == {"Work", "Health"}

    response = client.post("/finalize_day", json={"date": target_date}, headers=auth_headers)
    assert response.status_code == 200

    response = client.get("/entries", headers=auth_headers)
    entries = [e for e in response.get_json() if e["date"] == target_date]
    assert len(entries) == 2
    assert all(float(e["value"]) == 0 for e in entries)

    # ensure finalize_day is idempotent
    response = client.post("/finalize_day", json={"date": target_date}, headers=auth_headers)
    assert response.status_code == 200
    response = client.get("/entries", headers=auth_headers)
    entries = [e for e in response.get_json() if e["date"] == target_date]
    assert len(entries) == 2


def test_add_entry_validation(client, auth_headers):
    response = client.post(
        "/add_entry",
        json={"activity": "", "date": "2024-15-01"},
        headers=auth_headers,
    )
    assert response.status_code == 400
    body = response.get_json()
    assert body["error"]["code"] == "invalid_input"
    assert body["error"]["message"]

    long_note = "a" * 120
    response = client.post(
        "/add_entry",
        json={"activity": "Run", "date": "2024-01-01", "value": "abc", "note": long_note},
        headers=auth_headers,
    )
    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "invalid_input"


def test_rate_limit_enforced(client, auth_headers):
    from app import app

    original = app.config["RATE_LIMITS"]["add_entry"]
    app.config["RATE_LIMITS"]["add_entry"] = {"limit": 2, "window": 60}

    try:
        payload = {"date": "2024-01-01", "activity": "Test", "value": 1}
        r1 = client.post("/add_entry", json=payload, headers=auth_headers)
        assert r1.status_code in (200, 201)
        r2 = client.post("/add_entry", json=payload, headers=auth_headers)
        assert r2.status_code in (200, 201)
        r3 = client.post("/add_entry", json=payload, headers=auth_headers)
        assert r3.status_code == 429
        assert r3.get_json()["error"]["code"] == "too_many_requests"
    finally:
        app.config["RATE_LIMITS"]["add_entry"] = original


def test_login_rate_limit(client):
    from app import app

    username = f"user_{uuid.uuid4().hex[:8]}"
    password = "Passw0rd!"
    client.post("/register", json={"username": username, "password": password})

    original = app.config["RATE_LIMITS"]["login"]
    app.config["RATE_LIMITS"]["login"] = {"limit": 1, "window": 60}

    try:
        first = client.post("/login", json={"username": username, "password": password})
        assert first.status_code == 200
        second = client.post("/login", json={"username": username, "password": password})
        assert second.status_code == 429
        assert second.get_json()["error"]["code"] == "too_many_requests"
    finally:
        app.config["RATE_LIMITS"]["login"] = original


def test_api_key_enforced(client, auth_headers):
    from app import app

    app.config["API_KEY"] = "secret"
    try:
        resp = client.get("/entries", headers=auth_headers)
        assert resp.status_code == 401
        assert resp.get_json()["error"]["code"] in {"unauthorized", "bad_request"}

        headers_with_key = {**auth_headers, "X-API-Key": "secret"}
        resp = client.get("/entries", headers=headers_with_key)
        assert resp.status_code == 200
    finally:
        app.config["API_KEY"] = None


def test_import_csv_endpoint(client, auth_headers):
    csv_data = (
        "date,activity,value,note,description,category,goal\n"
        "2024-03-01,Swim,2,,Morning swim,Fitness,12\n"
    )
    data = {
        "file": (io.BytesIO(csv_data.encode("utf-8")), "activities.csv"),
    }
    response = client.post(
        "/import_csv",
        data=data,
        content_type="multipart/form-data",
        headers=auth_headers,
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["summary"]["created"] == 1

    # CSV import should have created an activity with category


def test_delete_entry_not_found_returns_standard_error(client, auth_headers):
    response = client.delete("/entries/9999", headers=auth_headers)
    assert response.status_code == 404
    body = response.get_json()
    assert body["error"]["code"] == "not_found"
    assert body["error"]["message"]


def test_invalid_stats_query_returns_standard_error(client, auth_headers):
    response = client.get("/stats/progress?group=invalid", headers=auth_headers)
    assert response.status_code == 400
    body = response.get_json()
    assert body["error"]["code"] == "invalid_query"
    assert body["error"]["message"]


def test_auth_is_required_for_entries(client):
    response = client.get("/entries")
    assert response.status_code == 401
    body = response.get_json()
    assert body["error"]["code"] == "unauthorized"


def test_csrf_is_required_for_mutations(client, auth_headers):
    headers_without_csrf = {k: v for k, v in auth_headers.items() if k != "X-CSRF-Token"}
    resp = client.post(
        "/add_activity",
        json={
            "name": "CSRF Test",
            "category": "Security",
            "frequency_per_day": 1,
            "frequency_per_week": 1,
            "description": "Testing",
        },
        headers=headers_without_csrf,
    )
    assert resp.status_code == 403
    assert resp.get_json()["error"]["code"] == "invalid_csrf"


def test_update_activity_propagates(client, auth_headers):
    client.post(
        "/add_activity",
        json={
            "name": "Meditation",
            "category": "Mind",
            "frequency_per_day": 1,
            "frequency_per_week": 7,
            "description": "Morning calm",
        },
        headers=auth_headers,
    )
    activity = client.get("/activities", headers=auth_headers).get_json()[0]

    client.post(
        "/add_entry",
        json={"date": "2024-04-01", "activity": "Meditation", "value": 1, "note": ""},
        headers=auth_headers,
    )

    update_payload = {
        "category": "Wellness",
        "frequency_per_day": 2,
        "frequency_per_week": 5,
        "description": "Updated desc",
    }
    resp = client.put(
        f"/activities/{activity['id']}",
        json=update_payload,
        headers=auth_headers,
    )
    assert resp.status_code == 200

    updated_activity = client.get("/activities", headers=auth_headers).get_json()[0]
    assert updated_activity["category"] == "Wellness"
    assert updated_activity["goal"] == pytest.approx((2 * 5) / 7)
    assert updated_activity["frequency_per_day"] == 2
    assert updated_activity["frequency_per_week"] == 5

    entries = client.get("/entries", headers=auth_headers).get_json()
    meditation_entry = next(e for e in entries if e["activity"] == "Meditation")
    assert meditation_entry["activity_description"] == "Updated desc"


def test_today_respects_deactivation_date(client, auth_headers):
    client.post(
        "/add_activity",
        json={
            "name": "Journal",
            "category": "Reflection",
            "frequency_per_day": 1,
            "frequency_per_week": 7,
            "description": "Daily journaling",
        },
        headers=auth_headers,
    )
    activity = client.get("/activities", headers=auth_headers).get_json()[0]
    activity_id = activity["id"]

    today = datetime.now()
    today_str = today.strftime("%Y-%m-%d")
    yesterday_str = (today - timedelta(days=1)).strftime("%Y-%m-%d")

    resp = client.get(f"/today?date={yesterday_str}", headers=auth_headers)
    assert any(row["name"] == "Journal" for row in resp.get_json())

    client.patch(f"/activities/{activity_id}/deactivate", headers=auth_headers)

    resp = client.get(f"/today?date={yesterday_str}", headers=auth_headers)
    assert any(row["name"] == "Journal" for row in resp.get_json())

    resp = client.get(f"/today?date={today_str}", headers=auth_headers)
    assert all(row["name"] != "Journal" for row in resp.get_json())


def test_entry_metadata_survives_activity_deletion(client, auth_headers):
    client.post(
        "/add_activity",
        json={
            "name": "Swim",
            "category": "Fitness",
            "frequency_per_day": 2,
            "frequency_per_week": 3,
            "description": "Pool laps",
        },
        headers=auth_headers,
    )
    client.post(
        "/add_entry",
        json={"date": "2024-05-01", "activity": "Swim", "value": 1, "note": ""},
        headers=auth_headers,
    )
    activity = client.get("/activities", headers=auth_headers).get_json()[0]
    client.patch(f"/activities/{activity['id']}/deactivate", headers=auth_headers)
    client.delete(f"/activities/{activity['id']}", headers=auth_headers)

    entries = client.get("/entries", headers=auth_headers).get_json()
    swim_entry = next(e for e in entries if e["activity"] == "Swim")
    assert swim_entry["category"] == "Fitness"
    assert swim_entry["activity_category"] == "Fitness"
    assert swim_entry["goal"] == pytest.approx((2 * 3) / 7)
    assert swim_entry["activity_goal"] == pytest.approx((2 * 3) / 7)


def test_entries_filtering(client, auth_headers):
    client.post(
        "/add_activity",
        json={
            "name": "Read",
            "category": "Leisure",
            "frequency_per_day": 1,
            "frequency_per_week": 7,
            "description": "Reading time",
        },
        headers=auth_headers,
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
        headers=auth_headers,
    )

    client.post(
        "/add_entry",
        json={"date": "2024-03-01", "activity": "Read", "value": 1, "note": ""},
        headers=auth_headers,
    )
    client.post(
        "/add_entry",
        json={"date": "2024-03-05", "activity": "Read", "value": 1, "note": ""},
        headers=auth_headers,
    )
    client.post(
        "/add_entry",
        json={"date": "2024-03-03", "activity": "Jog", "value": 2, "note": ""},
        headers=auth_headers,
    )

    resp = client.get("/entries?start_date=2024-03-02&end_date=2024-03-04", headers=auth_headers)
    assert resp.status_code == 200
    filtered = resp.get_json()
    assert len(filtered) == 1
    assert filtered[0]["activity"] == "Jog"

    resp = client.get("/entries?activity=Read", headers=auth_headers)
    assert resp.status_code == 200
    only_read = resp.get_json()
    assert {row["activity"] for row in only_read} == {"Read"}

    resp = client.get("/entries?category=Health", headers=auth_headers)
    assert resp.status_code == 200
    health_entries = resp.get_json()
    assert all(row["category"] == "Health" for row in health_entries)


def test_stats_progress_activity_and_category(client, auth_headers):
    client.post(
        "/add_activity",
        json={
            "name": "Coding",
            "category": "Work",
            "frequency_per_day": 1,
            "frequency_per_week": 7,
            "description": "",
        },
        headers=auth_headers,
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
        headers=auth_headers,
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
            headers=auth_headers,
        )

    activity_resp = client.get("/stats/progress?group=activity&period=30&date=2024-02-20", headers=auth_headers)
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
        "/stats/progress?group=category&period=30&date=2024-02-20",
        headers=auth_headers,
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


def test_entries_pagination(client, auth_headers):
    client.post(
        "/add_activity",
        json={
            "name": "Task",
            "category": "Testing",
            "frequency_per_day": 1,
            "frequency_per_week": 7,
            "description": "",
        },
        headers=auth_headers,
    )
    for day in range(1, 5):
        client.post(
            "/add_entry",
            json={
                "date": f"2024-03-0{day}",
                "activity": "Task",
                "value": day,
                "note": str(day),
            },
            headers=auth_headers,
        )

    first_page = client.get("/entries?limit=2", headers=auth_headers)
    assert first_page.status_code == 200
    assert len(first_page.get_json()) == 2

    second_page = client.get("/entries?limit=2&offset=2", headers=auth_headers)
    assert second_page.status_code == 200
    assert len(second_page.get_json()) == 2


def test_activities_pagination(client, auth_headers):
    for idx in range(5):
        client.post(
            "/add_activity",
            json={
                "name": f"Act {idx}",
                "category": "Cat",
                "frequency_per_day": 1,
                "frequency_per_week": 7,
                "description": "",
            },
            headers=auth_headers,
        )

    resp = client.get("/activities?limit=3", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.get_json()) == 3

    resp_all = client.get("/activities?all=true&limit=2&offset=3", headers=auth_headers)
    assert resp_all.status_code == 200
    assert len(resp_all.get_json()) == 2


def test_stats_pagination(client, auth_headers):
    for name in ("Alpha", "Beta", "Gamma"):
        client.post(
            "/add_activity",
            json={
                "name": name,
                "category": name,
                "frequency_per_day": 1,
                "frequency_per_week": 7,
                "description": "",
            },
            headers=auth_headers,
        )

    response = client.get("/stats/progress?group=activity&limit=2", headers=auth_headers)
    assert response.status_code == 200
    assert len(response.get_json()["data"]) == 2

    response_category = client.get("/stats/progress?group=category&limit=1", headers=auth_headers)
    assert response_category.status_code == 200
    assert len(response_category.get_json()["data"]) == 1


def test_today_pagination(client, auth_headers):
    for idx in range(5):
        client.post(
            "/add_activity",
            json={
                "name": f"Todo {idx}",
                "category": "Daily",
                "frequency_per_day": 1,
                "frequency_per_week": 7,
                "description": "",
            },
            headers=auth_headers,
        )

    resp = client.get("/today?limit=3", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.get_json()) == 3


def test_invalid_pagination_returns_error(client, auth_headers):
    resp = client.get("/activities?limit=abc", headers=auth_headers)
    assert resp.status_code == 400
    body = resp.get_json()
    assert body["error"]["code"] == "invalid_query"


def test_today_cache_invalidation(client, auth_headers):
    initial = client.get("/today", headers=auth_headers)
    assert initial.status_code == 200
    base_count = len(initial.get_json())

    client.post(
        "/add_activity",
        json={
            "name": "Cached Activity",
            "category": "Cache",
            "frequency_per_day": 1,
            "frequency_per_week": 7,
            "description": "",
        },
        headers=auth_headers,
    )

    refreshed = client.get("/today", headers=auth_headers)
    assert refreshed.status_code == 200
    assert len(refreshed.get_json()) == base_count + 1


def test_stats_cache_invalidation(client, auth_headers):
    client.post(
        "/add_activity",
        json={
            "name": "CacheStat",
            "category": "Cache",
            "frequency_per_day": 1,
            "frequency_per_week": 7,
            "description": "",
        },
        headers=auth_headers,
    )

    baseline = client.get(
        "/stats/progress?group=activity&date=2024-04-30",
        headers=auth_headers,
    )
    assert baseline.status_code == 200
    payload = baseline.get_json()
    cache_entry = next((row for row in payload["data"] if row["name"] == "CacheStat"), None)
    assert cache_entry is not None
    assert cache_entry["total_value"] == pytest.approx(0.0)

    client.post(
        "/add_entry",
        json={"date": "2024-04-01", "activity": "CacheStat", "value": 5, "note": ""},
        headers=auth_headers,
    )

    updated = client.get(
        "/stats/progress?group=activity&date=2024-04-30",
        headers=auth_headers,
    )
    assert updated.status_code == 200
    updated_payload = updated.get_json()
    updated_entry = next((row for row in updated_payload["data"] if row["name"] == "CacheStat"), None)
    assert updated_entry is not None
    assert updated_entry["total_value"] == pytest.approx(5.0)
