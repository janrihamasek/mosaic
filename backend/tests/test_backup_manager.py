import hashlib
import io
import uuid
import zipfile
from pathlib import Path

import app as app_module
import pytest
from app import app
from backup_manager import BackupManager
from extensions import db
from models import BackupSettings
from sqlalchemy import select


@pytest.fixture()
def auth_headers(client):
    import uuid

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


def make_auth_headers(client):
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


@pytest.fixture()
def backup_env(tmp_path, monkeypatch, client):
    backup_dir = tmp_path / "backups"
    app.config["BACKUP_DIR"] = str(backup_dir)
    new_manager = BackupManager(app)
    monkeypatch.setattr(app_module, "backup_manager", new_manager, raising=False)
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
    assert data["scheduler_running"] is True
    assert data["next_run_at"]


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
    assert backup_info["size_bytes"] > 0
    assert len(backup_info["sha256"]) == 64

    # Ensure the zip contains the expected files
    with zipfile.ZipFile(zip_path, "r") as archive:
        names = archive.namelist()
        assert backup_info["json"] in names
        assert backup_info["csv"] in names

    # Hash in payload matches actual file
    sha = hashlib.sha256(zip_path.read_bytes()).hexdigest()
    assert backup_info["sha256"] == sha

    status_resp = client.get("/backup/status", headers=auth_headers)
    status = status_resp.get_json()
    assert status["last_run"] is not None
    assert status["backups"]
    assert len(status["backups"][0]["sha256"]) == 64
    assert status["backups"][0]["sha256"] == sha
    assert status["scheduler_running"] is True
    assert status["next_run_at"]


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
    assert status["scheduler_running"] is True
    assert status["next_run_at"]

    # Reload settings directly from database to ensure persistence
    with app.app_context():
        settings = db.session.execute(select(BackupSettings)).scalar_one()
        assert settings.enabled is True
        assert settings.interval_minutes == 15

    disable_resp = client.post(
        "/backup/toggle", json={"enabled": False}, headers=auth_headers
    )
    assert disable_resp.status_code == 200
    assert disable_resp.get_json()["status"]["enabled"] is False


def test_backup_toggle_reports_next_run(client, auth_headers, backup_env):
    toggle_resp = client.post(
        "/backup/toggle",
        json={"enabled": True, "interval_minutes": 15},
        headers=auth_headers,
    )
    assert toggle_resp.status_code == 200
    status = toggle_resp.get_json()["status"]
    assert status["enabled"] is True
    assert status["interval_minutes"] == 15
    assert status["scheduler_running"] is True
    assert status["next_run_at"], status


def test_backup_download_endpoint(client, auth_headers, backup_env):
    run_resp = client.post("/backup/run", headers=auth_headers)
    assert run_resp.status_code == 200
    backup_filename = run_resp.get_json()["backup"]["zip"]

    download_resp = client.get(
        f"/backup/download/{backup_filename}", headers=auth_headers
    )
    assert download_resp.status_code == 200
    assert "zip" in (download_resp.headers.get("Content-Type") or "")

    content = download_resp.data
    with zipfile.ZipFile(io.BytesIO(content), "r") as archive:
        assert backup_filename.replace(".zip", ".json") in archive.namelist()


def test_backup_download_rejects_other_user(client, backup_env):
    # Create backup as user A
    headers_a = make_auth_headers(client)
    run_resp = client.post("/backup/run", headers=headers_a)
    assert run_resp.status_code == 200
    backup_filename = run_resp.get_json()["backup"]["zip"]

    # Attempt download as different user B should be rejected by filename validation
    headers_b = make_auth_headers(client)
    resp = client.get(f"/backup/download/{backup_filename}", headers=headers_b)
    assert resp.status_code == 400
    assert resp.get_json()["error"]["code"] == "invalid_input"


def test_backup_download_rejects_invalid_filename(client, auth_headers, backup_env):
    bad_names = [
        "../etc/passwd",
        "backup-2023-01-01.zip",
        "backup-20230101-010101.txt",
        "backup-20230101-010101.zip/../../x",
    ]
    for name in bad_names:
        resp = client.get(f"/backup/download/{name}", headers=auth_headers)
        assert resp.status_code == 400
        assert resp.get_json()["error"]["code"] == "invalid_input"


def test_backup_filename_validation_unit(backup_env):
    manager = backup_env
    assert manager._is_valid_backup_filename("backup-u1-20240101-010101.zip", 1)
    assert manager._is_valid_backup_filename("backup-u5-20231231-235959.json", 5)
    assert not manager._is_valid_backup_filename("", 1)
    assert not manager._is_valid_backup_filename("backup-u1-202401-010101.zip", 1)
    assert not manager._is_valid_backup_filename("backup-u2-20240101-010101.zip", 1)
    assert not manager._is_valid_backup_filename("../../../etc/passwd", 1)
