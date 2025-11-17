import uuid


def _create_user_headers(client):
    username = f"user_{uuid.uuid4().hex[:8]}"
    password = "Passw0rd!"
    register = client.post(
        "/register", json={"username": username, "password": password}
    )
    assert register.status_code == 201
    login = client.post("/login", json={"username": username, "password": password})
    assert login.status_code == 200
    tokens = login.get_json()
    return {
        "Authorization": f"Bearer {tokens['access_token']}",
        "X-CSRF-Token": tokens["csrf_token"],
    }


def test_cache_entries_are_namespaced_per_user(client):
    headers_a = _create_user_headers(client)
    headers_b = _create_user_headers(client)
    target_date = "2024-06-04"

    create_activity = client.post(
        "/add_activity",
        json={
            "name": "Namespaced Activity",
            "category": "Cache",
            "frequency_per_day": 1,
            "frequency_per_week": 7,
            "description": "Ensures cache scoped per user",
        },
        headers=headers_a,
    )
    assert create_activity.status_code == 201

    add_entry = client.post(
        "/add_entry",
        json={
            "date": target_date,
            "activity": "Namespaced Activity",
            "value": 1.0,
            "note": "",
        },
        headers=headers_a,
    )
    assert add_entry.status_code in {200, 201}

    today_a = client.get(f"/today?date={target_date}", headers=headers_a)
    assert today_a.status_code == 200
    today_payload_a = today_a.get_json()
    assert today_payload_a
    assert any(item["name"] == "Namespaced Activity" for item in today_payload_a)

    stats_a = client.get(f"/stats/progress?date={target_date}", headers=headers_a)
    assert stats_a.status_code == 200
    stats_payload_a = stats_a.get_json()
    assert stats_payload_a["goal_completion_today"] > 0
    assert stats_payload_a["positive_vs_negative"]["positive"] >= 1

    # Second calls warm caches for user A.
    cached_today_a = client.get(f"/today?date={target_date}", headers=headers_a)
    assert cached_today_a.get_json() == today_payload_a
    cached_stats_a = client.get(
        f"/stats/progress?date={target_date}", headers=headers_a
    )
    assert cached_stats_a.get_json() == stats_payload_a

    today_b = client.get(f"/today?date={target_date}", headers=headers_b)
    assert today_b.status_code == 200
    assert today_b.get_json() == []

    stats_b = client.get(f"/stats/progress?date={target_date}", headers=headers_b)
    assert stats_b.status_code == 200
    stats_payload_b = stats_b.get_json()
    assert stats_payload_b["goal_completion_today"] == 0
    assert stats_payload_b["positive_vs_negative"]["positive"] == 0
