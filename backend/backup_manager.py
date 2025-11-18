import csv
import json
import threading
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog
from db_utils import transactional_connection
from extensions import db
from repositories import backup_repo


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
        self._ensure_settings_row()
        self._ensure_scheduler()

    # ------------------------------------------------------------------ public API
    def create_backup(self, *, initiated_by: str = "manual") -> Dict[str, object]:
        with self._lock:
            now = datetime.now(timezone.utc)
            timestamp = now.strftime("%Y%m%d-%H%M%S")
            payload = self._fetch_database_payload()

            json_path = self.backup_dir / f"backup-{timestamp}.json"
            csv_path = self.backup_dir / f"backup-{timestamp}.csv"
            zip_path = self.backup_dir / f"backup-{timestamp}.zip"

            with json_path.open("w", encoding="utf-8") as fh:
                json.dump(
                    {
                        "generated_at": now.isoformat(),
                        "initiated_by": initiated_by,
                        "entries": payload["entries"],
                        "activities": payload["activities"],
                    },
                    fh,
                    ensure_ascii=False,
                    indent=2,
                )

            self._write_csv_dump(csv_path, payload["entries"], payload["activities"])

            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
                archive.write(json_path, arcname=json_path.name)
                archive.write(csv_path, arcname=csv_path.name)

            self._update_last_run(now)

            return {
                "timestamp": timestamp,
                "json": json_path.name,
                "csv": csv_path.name,
                "zip": zip_path.name,
                "generated_at": now.isoformat(),
            }

    def list_backups(self) -> List[Dict[str, object]]:
        backups: List[Dict[str, object]] = []
        for path in sorted(self.backup_dir.glob("backup-*.zip"), reverse=True):
            stats = path.stat()
            backups.append(
                {
                    "filename": path.name,
                    "size_bytes": stats.st_size,
                    "created_at": datetime.fromtimestamp(
                        stats.st_mtime, timezone.utc
                    ).isoformat(),
                }
            )
        return backups

    def get_status(self) -> Dict[str, object]:
        row: Optional[Dict[str, object]] = None

        with self.app.app_context():
            backup_repo.ensure_settings_row()
            row = backup_repo.fetch_settings()

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

        return {
            "enabled": enabled,
            "interval_minutes": interval,
            "last_run": last_run,
            "backups": self.list_backups(),
        }

    def toggle(
        self, enabled: Optional[bool] = None, interval_minutes: Optional[int] = None
    ) -> Dict[str, object]:
        if interval_minutes is not None:
            interval_minutes = max(int(interval_minutes), 5)

        with self.app.app_context():
            backup_repo.ensure_settings_row()
            row = backup_repo.fetch_settings() or {}
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

            backup_repo.update_settings(new_enabled, new_interval)

        return self.get_status()

    def get_backup_path(self, filename: str) -> Path:
        if "/" in filename or "\\" in filename or not filename.startswith("backup-"):
            raise ValueError("Invalid backup filename")
        path = self.backup_dir / filename
        if not path.exists():
            raise FileNotFoundError(f"Backup {filename} not found")
        return path

    # ------------------------------------------------------------------ internal helpers
    def _ensure_settings_row(self) -> None:
        with self.app.app_context():
            with transactional_connection(db.engine) as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS backup_settings (
                        id SERIAL PRIMARY KEY,
                        enabled BOOLEAN NOT NULL DEFAULT FALSE,
                        interval_minutes INTEGER NOT NULL DEFAULT 60,
                        last_run TIMESTAMPTZ
                    )
                    """
                )
                has_row = conn.execute("SELECT 1 FROM backup_settings LIMIT 1").scalar()
                if not has_row:
                    conn.execute(
                        "INSERT INTO backup_settings (enabled, interval_minutes) VALUES (?, ?)",
                        (False, 60),
                    )

    def _ensure_scheduler(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(
            target=self._scheduler_loop, name="backup-scheduler", daemon=True
        )
        self._thread.start()

    def _scheduler_loop(self) -> None:
        while not self._stop_event.is_set():
            status = self.get_status()
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
                    self.create_backup(initiated_by="scheduler")
                except Exception as exc:  # pragma: no cover - logged by Flask later
                    self.logger.exception("backup.scheduler_failed", error=str(exc))
                self._stop_event.wait(5)
            else:
                remaining = (interval * 60) - (now - last_run).total_seconds()
                self._stop_event.wait(max(5, min(remaining, 60)))

    def _fetch_database_payload(self) -> Dict[str, List[Dict[str, object]]]:
        with self.app.app_context():
            return backup_repo.fetch_database_payload()

    def _write_csv_dump(
        self,
        csv_path: Path,
        entries: List[Dict[str, object]],
        activities: List[Dict[str, object]],
    ) -> None:
        with csv_path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(
                [
                    "dataset",
                    "id",
                    "date",
                    "activity",
                    "value",
                    "note",
                    "category",
                    "goal",
                    "activity_type",
                ]
            )
            for row in entries:
                writer.writerow(
                    [
                        "entries",
                        row.get("id"),
                        row.get("date"),
                        row.get("activity"),
                        row.get("value"),
                        row.get("note"),
                        row.get("activity_category"),
                        row.get("activity_goal"),
                        row.get("activity_type"),
                    ]
                )
            writer.writerow([])
            writer.writerow(
                [
                    "dataset",
                    "id",
                    "name",
                    "category",
                    "activity_type",
                    "goal",
                    "description",
                    "active",
                    "frequency_per_day",
                    "frequency_per_week",
                ]
            )
            for row in activities:
                writer.writerow(
                    [
                        "activities",
                        row.get("id"),
                        row.get("name"),
                        row.get("category"),
                        row.get("activity_type"),
                        row.get("goal"),
                        row.get("description"),
                        row.get("active"),
                        row.get("frequency_per_day"),
                        row.get("frequency_per_week"),
                    ]
                )

    def _update_last_run(self, timestamp: datetime) -> None:
        with self.app.app_context():
            backup_repo.update_last_run(timestamp)

    @staticmethod
    def _parse_iso(value: Optional[str]) -> Optional[datetime]:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None
