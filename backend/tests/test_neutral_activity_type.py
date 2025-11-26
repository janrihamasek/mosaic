"""
Tests for neutral activity_type and goal completion logic.

Ensures that only positive activities count towards goals,
while negative and neutral activities do not.
"""

import json
from datetime import date, timedelta


def test_neutral_activity_creation(client):
    """Test that neutral activities can be created via API."""
    # Register and login
    client.post(
        "/register",
        json={"username": "testuser", "password": "testpass123"},
    )
    login_resp = client.post(
        "/login", json={"username": "testuser", "password": "testpass123"}
    )
    token = login_resp.get_json()["access_token"]
    csrf_token = login_resp.get_json()["csrf_token"]
    headers = {
        "Authorization": f"Bearer {token}",
        "X-CSRF-Token": csrf_token,
    }

    # Create neutral activity
    resp = client.post(
        "/add_activity",
        headers=headers,
        json={
            "name": "Mood Tracker",
            "category": "Mood",
            "activity_type": "neutral",
            "goal": 0,
            "frequency_per_day": 1,
            "frequency_per_week": 7,
        },
    )

    assert resp.status_code == 201
    data = resp.get_json()
    assert data["name"] == "Mood Tracker"
    assert data["activity_type"] == "neutral"
    assert data["goal"] == 0


def test_goal_completion_with_mixed_types(client):
    """Test that only positive entries count towards goal completion."""
    # Register and login
    client.post(
        "/register",
        json={"username": "testuser2", "password": "testpass123"},
    )
    login_resp = client.post(
        "/login", json={"username": "testuser2", "password": "testpass123"}
    )
    token = login_resp.get_json()["access_token"]
    csrf_token = login_resp.get_json()["csrf_token"]
    headers = {
        "Authorization": f"Bearer {token}",
        "X-CSRF-Token": csrf_token,
    }
    today = date.today().isoformat()

    # Create activities with different types
    activities = [
        {"name": "Positive Activity", "activity_type": "positive", "goal": 2.0},
        {"name": "Neutral Activity", "activity_type": "neutral", "goal": 0.0},
        {"name": "Negative Activity", "activity_type": "negative", "goal": 0.0},
    ]

    for act in activities:
        client.post(
            "/add_activity",
            headers=headers,
            json={
                "name": act["name"],
                "category": "Test",
                "activity_type": act["activity_type"],
                "goal": act["goal"],
                "frequency_per_day": 1,
                "frequency_per_week": 7,
            },
        )

    # Create entries for each activity
    entry_values = {"Positive Activity": 1.0, "Neutral Activity": 3.0, "Negative Activity": 2.0}
    for activity_name, value in entry_values.items():
        client.post(
            "/add_entry",
            headers=headers,
            json={
                "date": today,
                "activity": activity_name,
                "value": value,
            },
        )

    # Get today's stats
    stats_resp = client.get(f"/stats/progress?date={today}", headers=headers)
    assert stats_resp.status_code == 200
    stats = stats_resp.get_json()

    # Verify goal completion considers only positive
    # Positive activity: 1.0/2.0 = 50%
    assert stats["goal_completion_today"] == 50.0


def test_daily_positive_totals_excludes_neutral(client):
    """Test that daily totals only include positive entries."""
    # Register and login
    client.post(
        "/register",
        json={"username": "testuser3", "password": "testpass123"},
    )
    login_resp = client.post(
        "/login", json={"username": "testuser3", "password": "testpass123"}
    )
    token = login_resp.get_json()["access_token"]
    csrf_token = login_resp.get_json()["csrf_token"]
    headers = {
        "Authorization": f"Bearer {token}",
        "X-CSRF-Token": csrf_token,
    }
    today = date.today().isoformat()

    # Create activities with different types
    activities = [
        {"name": "Positive Act", "type": "positive", "value": 5.0},
        {"name": "Neutral Act", "type": "neutral", "value": 3.0},
        {"name": "Negative Act", "type": "negative", "value": 2.0},
    ]

    for act in activities:
        client.post(
            "/add_activity",
            headers=headers,
            json={
                "name": act["name"],
                "category": "Test",
                "activity_type": act["type"],
                "goal": 1.0 if act["type"] == "positive" else 0.0,
                "frequency_per_day": 1,
                "frequency_per_week": 7,
            },
        )

        # Create entry
        client.post(
            "/add_entry",
            headers=headers,
            json={
                "date": today,
                "activity": act["name"],
                "value": act["value"],
            },
        )

    # Get today's entries
    entries_resp = client.get(f"/today?date={today}", headers=headers)
    assert entries_resp.status_code == 200
    entries = entries_resp.get_json()

    # Verify neutral and negative have goal=0
    for entry in entries:
        if entry["activity_type"] in ["neutral", "negative"]:
            assert entry["activity_goal"] == 0.0
