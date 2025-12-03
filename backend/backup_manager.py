import hashlib
import json
import re
import threading
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog
from repositories import backup_repo
from sqlalchemy.exc import ProgrammingError
from services.backup_serializers import to_csv


class BackupManager:
    """Lightweight backup scheduler that creates JSON/CSV dumps of the Mosaic database."""

    def __init__(self, app):
        self.app = app
        self.logger = structlog.get_logger("mosaic.backup")
        backup_dir_config = app.config.get("BACKUP_DIR")
        if backup_dir_config:
            self.backup_dir = Path(backup_dir_config)
        else:
            self.backup_dir = Path(app.root_path) / "backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._initialized = False
        self._scheduler_user_id: Optional[int] = None

    def _ensure_initialized(self, user_id: int) -> None:
        """Lazy initialization - only connect to DB when actually needed."""
        if not self._initialized:
            self._ensure_settings_row(user_id)
            self._ensure_scheduler(user_id)
            self._initialized = True
        else:
            self._ensure_settings_row(user_id)

    # ------------------------------------------------------------------ public API
    def create_backup(
        self,
        *,
        initiated_by: str = "manual",
        user_id: int,
        is_admin: bool = False,
    ) -> Dict[str, object]:
        self._ensure_initialized(user_id)
        with self._lock:
            now = datetime.now(timezone.utc)
            timestamp = now.strftime("%Y%m%d-%H%M%S")
            payload = self._fetch_database_payload(user_id=user_id, is_admin=is_admin)

            prefix = f"backup-u{user_id or '0'}-{timestamp}"
            json_path = self.backup_dir / f"{prefix}.json"
            csv_path = self.backup_dir / f"{prefix}.csv"
            zip_path = self.backup_dir / f"{prefix}.zip"

            meta = {
                "entries": {
                    "limit": len(payload["entries"]),
                    "offset": 0,
                    "total": len(payload["entries"]),
                },
                "activities": {
                    "limit": len(payload["activities"]),
                    "offset": 0,
                    "total": len(payload["activities"]),
                },
            }
            with json_path.open("w", encoding="utf-8") as fh:
                json.dump(
                    {
                        "generated_at": now.isoformat(),
                        "initiated_by": initiated_by,
                        "entries": payload["entries"],
                        "activities": payload["activities"],
                        "meta": meta,
                    },
                    fh,
                    ensure_ascii=False,
                    indent=2,
                )

            self._write_csv_dump(csv_path, payload["entries"], payload["activities"])

            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
                archive.write(json_path, arcname=json_path.name)
                archive.write(csv_path, arcname=csv_path.name)

            self._update_last_run(now, user_id)
            sha256 = self._hash_file(zip_path)
            size_bytes = zip_path.stat().st_size

            return {
                "timestamp": timestamp,
                "json": json_path.name,
                "csv": csv_path.name,
                "zip": zip_path.name,
                "generated_at": now.isoformat(),
                "size_bytes": size_bytes,
                "sha256": sha256,
            }

    def list_backups(self, *, user_id: int) -> List[Dict[str, object]]:
        backups: List[Dict[str, object]] = []
        pattern = f"backup-u{user_id}-*.zip"
        for path in sorted(self.backup_dir.glob(pattern), reverse=True):
            stats = path.stat()
            backups.append(
                {
                    "filename": path.name,
                    "size_bytes": stats.st_size,
                    "created_at": datetime.fromtimestamp(
                        stats.st_mtime, timezone.utc
                    ).isoformat(),
                    "sha256": self._hash_file(path),
                }
            )
        return backups

    def get_status(self, *, user_id: int) -> Dict[str, object]:
        self._ensure_initialized(user_id)
        row: Optional[Dict[str, object]] = None

        with self.app.app_context():
            backup_repo.ensure_settings_row(user_id)
            try:
                row = backup_repo.fetch_settings(user_id)
            except ProgrammingError:
                # Table might not exist yet (e.g., fresh DB); ensure and retry.
                backup_repo.ensure_settings_row(user_id)
                row = backup_repo.fetch_settings(user_id)

        enabled_raw: Any = row["enabled"] if row else False
        interval_raw: Any = row["interval_minutes"] if row else 60
        last_run_value: Any = row["last_run"] if row else None

        enabled = bool(enabled_raw)
        if isinstance(interval_raw, (int, float, str)):
            interval = int(interval_raw)
        else:
            interval = 60

        if isinstance(last_run_value, datetime):
            last_run = last_run_value.isoformat()
        else:
            last_run = last_run_value

        scheduler_running = bool(
            self._thread and self._thread.is_alive() and not self._stop_event.is_set()
        )
        now = datetime.now(timezone.utc)
        last_run_dt = self._parse_iso(last_run) if isinstance(last_run, str) else None
        next_run_at: Optional[str] = None
        # Always expose a future timestamp based on interval and last_run (even if disabled)
        if last_run_dt:
            eta_seconds = max(
                interval * 60 - (now - last_run_dt).total_seconds(), 0
            )
            next_run_at = (now + timedelta(seconds=eta_seconds)).isoformat()
        else:
            next_run_at = (now + timedelta(minutes=interval)).isoformat()

        return {
            "enabled": enabled,
            "interval_minutes": interval,
            "last_run": last_run,
            "backups": self.list_backups(user_id=user_id),
            "scheduler_running": scheduler_running,
            "next_run_at": next_run_at,
        }

    def toggle(
        self, *, user_id: int, enabled: Optional[bool] = None, interval_minutes: Optional[int] = None
    ) -> Dict[str, object]:
        self._ensure_initialized(user_id)
        if interval_minutes is not None:
            interval_minutes = max(int(interval_minutes), 5)

        with self.app.app_context():
            backup_repo.ensure_settings_row(user_id)
            row = backup_repo.fetch_settings(user_id) or {}
            existing_enabled_raw: Any = row.get("enabled", False)
            existing_interval_raw: Any = row.get("interval_minutes", 60)

            new_enabled = (
                bool(existing_enabled_raw) if enabled is None else bool(enabled)
            )

            candidate_interval = interval_minutes
            if candidate_interval is None:
                if isinstance(existing_interval_raw, (int, float, str)):
                    candidate_interval = int(existing_interval_raw)
                else:
                    candidate_interval = 60
            else:
                candidate_interval = int(candidate_interval)
            new_interval = candidate_interval

            backup_repo.update_settings(user_id, new_enabled, new_interval)

        return self.get_status(user_id=user_id)

    def get_backup_path(self, filename: str, *, user_id: int) -> Path:
        if not self._is_valid_backup_filename(filename, user_id=user_id):
            raise ValueError("Invalid backup filename")

        candidate = self.backup_dir / filename
        backup_root = self.backup_dir.resolve()
        try:
            path = candidate.resolve(strict=True)
        except FileNotFoundError:
            raise FileNotFoundError(f"Backup {filename} not found")

        # Prevent path traversal by ensuring resolved path stays under backup_dir.
        if backup_root not in path.parents and path != backup_root:
            raise ValueError("Invalid backup filename")
        return path

    # ------------------------------------------------------------------ internal helpers
    def _ensure_settings_row(self, user_id: int) -> None:
        with self.app.app_context():
            backup_repo.ensure_settings_row(user_id)

    def _ensure_scheduler(self, user_id: int) -> None:
        if self._thread and self._thread.is_alive():
            self._scheduler_user_id = user_id
            return
        self._scheduler_user_id = user_id
        self._thread = threading.Thread(
            target=self._scheduler_loop, name="backup-scheduler", daemon=True
        )
        self._thread.start()

    def _scheduler_loop(self) -> None:
        self._scheduler_user_id: Optional[int] = getattr(self, "_scheduler_user_id", None)
        while not self._stop_event.is_set():
            if self._scheduler_user_id is None:
                self._stop_event.wait(5)
                continue
            try:
                status = self.get_status(user_id=self._scheduler_user_id)
            except Exception as exc:  # pragma: no cover - log and retry later
                self.logger.exception("backup.scheduler_status_error", error=str(exc))
                self._stop_event.wait(10)
                continue

            if not status["enabled"]:
                self._stop_event.wait(30)
                continue

            raw_interval = status.get("interval_minutes", 60)
            try:
                interval_value = int(raw_interval)  # type: ignore[arg-type]
            except (TypeError, ValueError):
                interval_value = 60
            interval = max(interval_value, 5)
            raw_last_run = status.get("last_run")
            last_run = self._parse_iso(
                raw_last_run if isinstance(raw_last_run, str) else None
            )
            now = datetime.now(timezone.utc)

            if last_run is None or (now - last_run).total_seconds() >= interval * 60:
                try:
                    self.create_backup(initiated_by="scheduler", user_id=self._scheduler_user_id)
                except Exception as exc:  # pragma: no cover - logged by Flask later
                    self.logger.exception("backup.scheduler_failed", error=str(exc))
                self._stop_event.wait(5)
            else:
                remaining = (interval * 60) - (now - last_run).total_seconds()
                self._stop_event.wait(max(5, min(remaining, 60)))

    def _fetch_database_payload(
        self, *, user_id: int, is_admin: bool
    ) -> Dict[str, List[Dict[str, object]]]:
        with self.app.app_context():
            return {
                "entries": backup_repo.get_export_entries_all(user_id, is_admin=False),
                "activities": backup_repo.get_export_activities_all(
                    user_id, is_admin=False
                ),
            }

    def _write_csv_dump(
        self,
        csv_path: Path,
        entries: List[Dict[str, object]],
        activities: List[Dict[str, object]],
    ) -> None:
        csv_text = to_csv(entries, activities)
        with csv_path.open("w", newline="", encoding="utf-8") as fh:
            fh.write(csv_text)

    def _update_last_run(self, timestamp: datetime, user_id: int) -> None:
        with self.app.app_context():
            backup_repo.update_last_run(timestamp, user_id)

    @staticmethod
    def _parse_iso(value: Optional[str]) -> Optional[datetime]:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None

    @staticmethod
    def _hash_file(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as fh:
            for chunk in iter(lambda: fh.read(8192), b""):
                digest.update(chunk)
        return digest.hexdigest()

    @staticmethod
    def _is_valid_backup_filename(
        filename: str, user_id: int
    ) -> bool:
        # Enforce backup-u<id>-YYYYMMDD-HHMMSS.{json,csv,zip} pattern and reject traversal
        if not filename or len(filename) > 96:
            return False
        user_part = f"u{user_id}"
        pattern = rf"^backup-{user_part}-\d{{8}}-\d{{6}}\.(json|csv|zip)$"
        return bool(re.match(pattern, filename))
