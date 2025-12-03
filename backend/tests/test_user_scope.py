import csv
import io
import uuid
from typing import Dict

import pytest
from app import app
from extensions import db
from models import Activity, Entry, User
from sqlalchemy import select


def _auth_headers(client, username: str | None = None) -> Dict[str, str]:
    username = username or f"user_{uuid.uuid4().hex[:8]}"
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


def test_multi_user_isolation(client):
    headers_a = _auth_headers(client, "user_scope_a")
    headers_b = _auth_headers(client, "user_scope_b")

    activity_payload = {
        "name": "SharedName",
        "category": "Leisure",
        "frequency_per_day": 1,
        "frequency_per_week": 1,
        "description": "Scoped activity",
    }
    for headers in (headers_a, headers_b):
        resp = client.post("/add_activity", json=activity_payload, headers=headers)
        assert resp.status_code == 201

    entry_payload = {
        "date": "2024-04-01",
        "activity": "SharedName",
        "value": 1,
        "note": "per-user",
    }
    resp = client.post("/add_entry", json=entry_payload, headers=headers_a)
    assert resp.status_code in (200, 201)
    resp = client.post("/add_entry", json=entry_payload, headers=headers_b)
    assert resp.status_code in (200, 201)

    activities_a = client.get("/activities", headers=headers_a).get_json()
    activities_b = client.get("/activities", headers=headers_b).get_json()
    assert len(activities_a) == 1
    assert len(activities_b) == 1
    assert activities_a[0]["name"] == "SharedName"
    assert activities_b[0]["name"] == "SharedName"
    assert activities_a != activities_b  # different user_ids behind the scenes

    entries_a = client.get("/entries", headers=headers_a).get_json()
    entries_b = client.get("/entries", headers=headers_b).get_json()
    assert len(entries_a) == 1
    assert len(entries_b) == 1
    assert entries_a[0]["activity"] == "SharedName"
    assert entries_b[0]["activity"] == "SharedName"
    # Ensure no leakage by comparing IDs
    assert entries_a[0]["id"] != entries_b[0]["id"]


def test_export_import_round_trip_between_users(client):
    # Seed data for first user and export CSV
    headers_source = _auth_headers(client, "export_source")
    client.post(
        "/add_activity",
        json={
            "name": "Reading",
            "category": "Leisure",
            "frequency_per_day": 1,
            "frequency_per_week": 7,
            "description": "Books",
        },
        headers=headers_source,
    )
    client.post("/add_entry", json={"date": "2024-05-01", "activity": "Reading", "value": 2}, headers=headers_source)
    client.post("/add_entry", json={"date": "2024-05-02", "activity": "Reading", "value": 3}, headers=headers_source)

    export_resp = client.get("/export/csv", headers=headers_source)
    assert export_resp.status_code == 200
    export_body = export_resp.data

    # Create new user and import the exported CSV
    headers_target = _auth_headers(client, "export_target")
    import_resp = client.post(
        "/import_csv",
        data={"file": (io.BytesIO(export_body), "export.csv")},
        headers=headers_target,
        content_type="multipart/form-data",
    )
    assert import_resp.status_code == 200

    with app.app_context():
        target_user = db.session.execute(select(User).where(User.username == "export_target")).scalar_one()
        activities = db.session.execute(
            select(Activity).where(Activity.user_id == target_user.id, Activity.name == "Reading")
        ).scalars().all()
        entries = db.session.execute(
            select(Entry).where(Entry.user_id == target_user.id).order_by(Entry.date)
        ).scalars().all()
        assert len(activities) == 1
        assert len(entries) == 2
        assert [e.value for e in entries] == [2.0, 3.0]

    # Ensure original export format remains unchanged (dataset column present)
    reader = csv.reader(io.StringIO(export_body.decode("utf-8")))
    datasets = {row[0] for row in reader if row}
    assert "entries" in datasets
    assert "activities" in datasets


def test_backup_download_access_is_user_scoped(client):
    # Unauthenticated access blocked
    status_resp = client.get("/backup/status")
    run_resp = client.post("/backup/run")
    assert status_resp.status_code == 401
    assert run_resp.status_code == 401

    headers_owner = _auth_headers(client, "backup_owner")
    headers_other = _auth_headers(client, "backup_other")

    run_resp = client.post("/backup/run", headers=headers_owner)
    assert run_resp.status_code == 200
    backup_info = run_resp.get_json()["backup"]
    backup_filename = backup_info["zip"]

    # Owner can download
    download_owner = client.get(f"/backup/download/{backup_filename}", headers=headers_owner)
    assert download_owner.status_code == 200
    assert "zip" in (download_owner.headers.get("Content-Type") or "")

    # Other user cannot access owner's backup
    download_other = client.get(f"/backup/download/{backup_filename}", headers=headers_other)
    assert download_other.status_code in (400, 404)
