import io
import sqlite3
import zipfile
from pathlib import Path

import pytest

import app as app_module
from app import app
from backup_manager import BackupManager


@pytest.fixture()
def auth_headers(client):
    import uuid

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


@pytest.fixture()
def backup_env(tmp_path, monkeypatch, client):
    backup_dir = tmp_path / "backups"
    app.config["BACKUP_DIR"] = str(backup_dir)
    new_manager = BackupManager(app)
    monkeypatch.setattr(app_module, "backup_manager", new_manager)
    setattr(app, "backup_manager", new_manager)
    return new_manager


def test_backup_status_defaults(client, auth_headers, backup_env):
    response = client.get("/backup/status", headers=auth_headers)
    assert response.status_code == 200
    data = response.get_json()
    assert data["enabled"] is False
    assert data["interval_minutes"] == 60
    assert data["backups"] == []
    assert data["last_run"] is None


def test_backup_run_creates_files(client, auth_headers, backup_env, tmp_path):
    run_resp = client.post("/backup/run", headers=auth_headers)
    assert run_resp.status_code == 200
    payload = run_resp.get_json()
    backup_info = payload["backup"]

    backup_dir = Path(app.config["BACKUP_DIR"])
    assert (backup_dir / backup_info["json"]).exists()
    assert (backup_dir / backup_info["csv"]).exists()
    zip_path = backup_dir / backup_info["zip"]
    assert zip_path.exists()

    # Ensure the zip contains the expected files
    with zipfile.ZipFile(zip_path, "r") as archive:
        names = archive.namelist()
        assert backup_info["json"] in names
        assert backup_info["csv"] in names

    status_resp = client.get("/backup/status", headers=auth_headers)
    status = status_resp.get_json()
    assert status["last_run"] is not None
    assert status["backups"]


def test_backup_toggle_persistence(client, auth_headers, backup_env):
    toggle_resp = client.post(
        "/backup/toggle",
        json={"enabled": True, "interval_minutes": 15},
        headers=auth_headers,
    )
    assert toggle_resp.status_code == 200
    status = toggle_resp.get_json()["status"]
    assert status["enabled"] is True
    assert status["interval_minutes"] == 15

    # Reload settings directly from database to ensure persistence
    conn = sqlite3.connect(app.config["DB_PATH"])
    try:
        row = conn.execute(
            "SELECT enabled, interval_minutes FROM backup_settings ORDER BY id ASC LIMIT 1"
        ).fetchone()
        assert row is not None
        assert row[0] == 1
        assert row[1] == 15
    finally:
        conn.close()

    disable_resp = client.post("/backup/toggle", json={"enabled": False}, headers=auth_headers)
    assert disable_resp.status_code == 200
    assert disable_resp.get_json()["status"]["enabled"] is False


def test_backup_download_endpoint(client, auth_headers, backup_env):
    run_resp = client.post("/backup/run", headers=auth_headers)
    assert run_resp.status_code == 200
    backup_filename = run_resp.get_json()["backup"]["zip"]

    download_resp = client.get(f"/backup/download/{backup_filename}", headers=auth_headers)
    assert download_resp.status_code == 200
    assert "zip" in (download_resp.headers.get("Content-Type") or "")

    content = download_resp.data
    with zipfile.ZipFile(io.BytesIO(content), "r") as archive:
        assert backup_filename.replace(".zip", ".json") in archive.namelist()
