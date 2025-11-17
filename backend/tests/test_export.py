import csv
import io
import uuid

import pytest


@pytest.fixture()
def auth_headers(client):
    username = f"user_{uuid.uuid4().hex[:8]}"
    password = "Passw0rd!"
    register_resp = client.post(
        "/register", json={"username": username, "password": password}
    )
    assert register_resp.status_code == 201
    login_resp = client.post(
        "/login", json={"username": username, "password": password}
    )
    assert login_resp.status_code == 200
    tokens = login_resp.get_json()
    return {
        "Authorization": f"Bearer {tokens['access_token']}",
        "X-CSRF-Token": tokens["csrf_token"],
    }


def _seed_sample_data(client, headers):
    activities = [
        {
            "name": "Reading",
            "category": "Leisure",
            "frequency_per_day": 1,
            "frequency_per_week": 7,
            "description": "Read a book",
        },
        {
            "name": "Running",
            "category": "Health",
            "frequency_per_day": 2,
            "frequency_per_week": 4,
            "description": "Morning jog",
        },
    ]
    for payload in activities:
        response = client.post("/add_activity", json=payload, headers=headers)
        assert response.status_code == 201

    entries = [
        {
            "date": "2024-03-01",
            "activity": "Reading",
            "value": 1,
            "note": "Finished chapter",
        },
        {"date": "2024-03-02", "activity": "Running", "value": 5, "note": "5km run"},
    ]
    for payload in entries:
        response = client.post("/add_entry", json=payload, headers=headers)
        assert response.status_code in (200, 201)


def test_export_requires_authentication(client):
    json_resp = client.get("/export/json")
    csv_resp = client.get("/export/csv")
    assert json_resp.status_code == 401
    assert csv_resp.status_code == 401


def test_export_json_includes_entries_and_activities(client, auth_headers):
    _seed_sample_data(client, auth_headers)

    response = client.get("/export/json?limit=1", headers=auth_headers)
    assert response.status_code == 200
    assert response.headers["Content-Type"].startswith("application/json")
    disposition = response.headers.get("Content-Disposition", "")
    assert disposition.startswith("attachment;")
    assert disposition.endswith('.json"') or disposition.endswith(".json")

    payload = response.get_json()
    assert payload["meta"]["entries"]["limit"] == 1
    assert payload["meta"]["entries"]["total"] == 2
    assert payload["meta"]["activities"]["total"] == 2
    assert len(payload["entries"]) == 1
    assert len(payload["activities"]) == 1
    assert payload["entries"][0]["activity"] == "Reading"
    assert payload["activities"][0]["name"] == "Reading"
    assert response.headers["X-Total-Entries"] == "2"
    assert response.headers["X-Total-Activities"] == "2"


def test_export_pagination_offset(client, auth_headers):
    _seed_sample_data(client, auth_headers)
    response = client.get("/export/json?limit=1&offset=1", headers=auth_headers)
    assert response.status_code == 200

    payload = response.get_json()
    assert len(payload["entries"]) == 1
    assert payload["entries"][0]["activity"] == "Running"
    assert payload["meta"]["entries"]["offset"] == 1


def test_export_csv_format(client, auth_headers):
    _seed_sample_data(client, auth_headers)
    response = client.get("/export/csv?limit=1", headers=auth_headers)
    assert response.status_code == 200
    assert response.headers["Content-Type"].startswith("text/csv")
    assert response.headers["X-Total-Entries"] == "2"
    assert response.headers["X-Total-Activities"] == "2"

    csv_text = response.data.decode("utf-8")
    reader = csv.reader(io.StringIO(csv_text))

    entries_header = next(reader)
    assert entries_header[:4] == ["dataset", "entry_id", "date", "activity"]

    entry_row = next(reader)
    assert entry_row[0] == "entries"
    assert entry_row[3] == "Reading"

    # Advance to the blank separator row between sections
    for row in reader:
        if not any(row):
            break

    activities_header = next(reader)
    assert activities_header[:3] == ["dataset", "activity_id", "name"]

    activity_row = next(reader)
    assert activity_row[0] == "activities"
    assert activity_row[2] == "Reading"
