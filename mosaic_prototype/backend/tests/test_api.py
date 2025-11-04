import io
import uuid
from datetime import datetime, timedelta

import pytest

from app import _cache_storage


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


def test_stats_progress_payload_structure(client, auth_headers):
    activities = [
        {
            "name": "Walking",
            "category": "Health",
            "frequency_per_day": 1,
            "frequency_per_week": 7,
            "description": "Daily walk",
        },
        {
            "name": "Reading",
            "category": "Art",
            "frequency_per_day": 1,
            "frequency_per_week": 7,
            "description": "Leisure time",
        },
        {
            "name": "Coding",
            "category": "Work",
            "frequency_per_day": 1,
            "frequency_per_week": 5,
            "description": "Focus session",
        },
    ]
    for payload in activities:
        resp = client.post("/add_activity", json=payload, headers=auth_headers)
        assert resp.status_code == 201

    sample_entries = [
        ("2024-05-30", "Walking", 1.0),
        ("2024-05-30", "Reading", 1.0),
        ("2024-05-29", "Walking", 1.0),
        ("2024-05-28", "Coding", 0.2),
        ("2024-05-27", "Coding", 1.0),
        ("2024-05-20", "Reading", 1.0),
        ("2024-05-10", "Coding", 0.6),
    ]
    for date, activity, value in sample_entries:
        resp = client.post(
            "/add_entry",
            json={"date": date, "activity": activity, "value": value, "note": ""},
            headers=auth_headers,
        )
        assert resp.status_code in {200, 201}

    response = client.get("/stats/progress?date=2024-05-30", headers=auth_headers)
    assert response.status_code == 200
    payload = response.get_json()

    expected_keys = {
        "goal_completion_today",
        "streak_length",
        "activity_distribution",
        "avg_goal_fulfillment",
        "active_days_ratio",
        "positive_vs_negative",
        "avg_goal_fulfillment_by_category",
        "top_consistent_activities_by_category",
    }
    assert expected_keys.issubset(payload.keys())

    assert isinstance(payload["goal_completion_today"], (int, float))
    assert 0.0 <= payload["goal_completion_today"] <= 100.0
    assert pytest.approx(payload["goal_completion_today"], rel=0, abs=0.05) == round(
        payload["goal_completion_today"], 1
    )

    assert isinstance(payload["streak_length"], int)
    assert payload["streak_length"] >= 0

    distribution = payload["activity_distribution"]
    assert isinstance(distribution, list) and distribution
    total_percent = 0.0
    total_count = 0
    for bucket in distribution:
        assert {"category", "count", "percent"}.issubset(bucket.keys())
        assert isinstance(bucket["category"], str)
        assert isinstance(bucket["count"], int)
        assert bucket["count"] >= 0
        assert isinstance(bucket["percent"], (int, float))
        assert 0.0 <= bucket["percent"] <= 100.0
        total_percent += bucket["percent"]
        total_count += bucket["count"]
    assert total_count > 0
    assert pytest.approx(100.0, abs=0.6) == total_percent

    averages = payload["avg_goal_fulfillment"]
    assert set(averages.keys()) == {"last_7_days", "last_30_days"}
    for value in averages.values():
        assert isinstance(value, (int, float))
        assert 0.0 <= value <= 100.0
        assert pytest.approx(value, rel=0, abs=0.05) == round(value, 1)

    active_ratio = payload["active_days_ratio"]
    assert {"active_days", "total_days", "percent"} == set(active_ratio.keys())
    assert isinstance(active_ratio["active_days"], int)
    assert isinstance(active_ratio["total_days"], int)
    assert active_ratio["total_days"] == 30
    assert 0 <= active_ratio["active_days"] <= 30
    assert isinstance(active_ratio["percent"], (int, float))
    assert pytest.approx(active_ratio["percent"], rel=0, abs=0.05) == round(active_ratio["percent"], 1)

    polarity = payload["positive_vs_negative"]
    assert {"positive", "negative", "ratio"} == set(polarity.keys())
    assert isinstance(polarity["positive"], int)
    assert isinstance(polarity["negative"], int)
    assert polarity["positive"] >= 0 and polarity["negative"] >= 0
    assert isinstance(polarity["ratio"], (int, float))
    assert polarity["ratio"] >= 0.0

    avg_by_category = payload["avg_goal_fulfillment_by_category"]
    assert isinstance(avg_by_category, list)
    for item in avg_by_category:
        assert {"category", "last_7_days", "last_30_days"} == set(item.keys())
        assert isinstance(item["category"], str)
        for key in ("last_7_days", "last_30_days"):
            assert isinstance(item[key], (int, float))
            assert 0.0 <= item[key] <= 100.0
            assert pytest.approx(item[key], rel=0, abs=0.05) == round(item[key], 1)

    consistent = payload["top_consistent_activities_by_category"]
    assert isinstance(consistent, list)
    for bucket in consistent:
        assert {"category", "activities"} == set(bucket.keys())
        assert isinstance(bucket["category"], str)
        assert isinstance(bucket["activities"], list)
        assert len(bucket["activities"]) <= 3
        for entry in bucket["activities"]:
            assert {"name", "consistency_percent"} == set(entry.keys())
            assert isinstance(entry["name"], str)
            assert isinstance(entry["consistency_percent"], (int, float))
            assert 0.0 <= entry["consistency_percent"] <= 100.0
            assert pytest.approx(entry["consistency_percent"], rel=0, abs=0.05) == round(
                entry["consistency_percent"], 1
            )


def test_stats_progress_invalid_date(client, auth_headers):
    response = client.get("/stats/progress?date=2024-13-01", headers=auth_headers)
    assert response.status_code == 400
    body = response.get_json()
    assert body["error"]["code"] == "invalid_query"
    assert body["error"]["message"]


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
    _cache_storage.clear()
    target_date = "2024-06-01"
    cache_key = f"stats::dashboard::{target_date}"

    resp = client.post(
        "/add_activity",
        json={
            "name": "CacheStat",
            "category": "Cache",
            "frequency_per_day": 1,
            "frequency_per_week": 7,
            "description": "Cache tracker",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201

    baseline = client.get(f"/stats/progress?date={target_date}", headers=auth_headers)
    assert baseline.status_code == 200
    initial_payload = baseline.get_json()
    assert cache_key in _cache_storage
    assert initial_payload["goal_completion_today"] == pytest.approx(0.0)
    baseline_positive = initial_payload["positive_vs_negative"]["positive"]

    resp = client.post(
        "/add_entry",
        json={"date": target_date, "activity": "CacheStat", "value": 1.0, "note": ""},
        headers=auth_headers,
    )
    assert resp.status_code in {200, 201}
    assert cache_key not in _cache_storage

    updated = client.get(f"/stats/progress?date={target_date}", headers=auth_headers)
    assert updated.status_code == 200
    updated_payload = updated.get_json()
    assert updated_payload["goal_completion_today"] > initial_payload["goal_completion_today"]
    assert updated_payload["positive_vs_negative"]["positive"] == baseline_positive + 1
    assert cache_key in _cache_storage

    resp = client.post(
        "/add_activity",
        json={
            "name": "AnotherStat",
            "category": "New",
            "frequency_per_day": 1,
            "frequency_per_week": 7,
            "description": "Second tracker",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201
    assert cache_key not in _cache_storage
