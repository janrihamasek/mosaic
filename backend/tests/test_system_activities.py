import uuid


def _register_and_login(client):
    username = f"user_{uuid.uuid4().hex[:8]}"
    password = "Passw0rd!"
    register_resp = client.post("/register", json={"username": username, "password": password})
    assert register_resp.status_code == 201
    login_resp = client.post("/login", json={"username": username, "password": password})
    assert login_resp.status_code == 200
    tokens = login_resp.get_json()
    headers = {
        "Authorization": f"Bearer {tokens['access_token']}",
        "X-CSRF-Token": tokens["csrf_token"],
    }
    return headers, username


def _get_activities(client, headers, include_all=False):
    flag = "true" if include_all else "false"
    resp = client.get(f"/activities?all={flag}", headers=headers)
    assert resp.status_code == 200
    return resp.get_json()


def _find_mood(activities):
    return next((a for a in activities if a["name"] == "Mood"), None)


def test_mood_seeded_for_every_user(client):
    headers_one, _ = _register_and_login(client)
    headers_two, _ = _register_and_login(client)

    activities_one = _get_activities(client, headers_one, include_all=True)
    activities_two = _get_activities(client, headers_two, include_all=True)

    mood_one = _find_mood(activities_one)
    mood_two = _find_mood(activities_two)

    assert mood_one is not None
    assert mood_two is not None
    assert bool(mood_one.get("is_system")) is True
    assert bool(mood_two.get("is_system")) is True
    assert mood_one["user_id"] != mood_two["user_id"]


def test_system_mood_can_be_deactivated_but_not_deleted(client):
    headers, _ = _register_and_login(client)
    activities = _get_activities(client, headers, include_all=True)
    mood = _find_mood(activities)
    assert mood is not None

    delete_resp = client.delete(f"/activities/{mood['id']}", headers=headers)
    assert delete_resp.status_code == 422
    delete_body = delete_resp.get_json()
    assert delete_body["error"]["code"] == "system_activity"

    deactivate_resp = client.patch(f"/activities/{mood['id']}/deactivate", headers=headers)
    assert deactivate_resp.status_code == 200

    refreshed = _get_activities(client, headers, include_all=True)
    refreshed_mood = _find_mood(refreshed)
    assert refreshed_mood is not None
    assert refreshed_mood["active"] == 0
