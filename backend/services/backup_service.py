"""
Backup service.

Wraps backup scheduling, status reporting, toggling, and export helpers without
any Flask HTTP dependencies.
"""

from pathlib import Path
from typing import Any, Dict, List, Tuple

from audit import log_event
from backup_manager import BackupManager
from repositories import backup_repo
from services.backup_serializers import to_csv
from security import ValidationError


def get_backup_status(manager: BackupManager, *, user_id: int | None) -> Dict:
    try:
        return manager.get_status(user_id=user_id)
    except Exception as exc:
        raise ValidationError(str(exc), code="backup_error", status=500)


def run_backup(
    manager: BackupManager, *, operator_id: int | None, user_id: int | None
) -> Tuple[Dict[str, object], int]:
    try:
        result = manager.create_backup(
            initiated_by="api", user_id=user_id, is_admin=False
        )
    except Exception as exc:
        log_event(
            "backup.run_failed",
            "Backup creation failed",
            user_id=operator_id,
            level="error",
            context={"error": str(exc)},
        )
        raise ValidationError(
            "Failed to create backup", code="backup_error", status=500
        )
    log_event(
        "backup.run",
        "Backup created",
        user_id=operator_id,
        context={"backup": result},
    )
    return {"message": "Backup completed", "backup": result}, 200


def toggle_backup(
    manager: BackupManager, *, operator_id: int | None, payload: Dict[str, object]
) -> Tuple[Dict[str, object], int]:
    enabled = payload.get("enabled")
    interval = payload.get("interval_minutes")

    if enabled is not None and not isinstance(enabled, bool):
        raise ValidationError(
            "enabled must be a boolean", code="invalid_input", status=400
        )
    if interval is not None:
        try:
            interval = int(interval)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            raise ValidationError(
                "interval_minutes must be an integer", code="invalid_input", status=400
            )
        if interval < 5:
            raise ValidationError(
                "interval_minutes must be at least 5", code="invalid_input", status=400
            )

    try:
        status = manager.toggle(enabled=enabled, interval_minutes=interval)
    except Exception as exc:
        log_event(
            "backup.toggle_failed",
            "Backup settings update failed",
            user_id=operator_id,
            level="error",
            context={"error": str(exc)},
        )
        raise ValidationError(
            "Unable to update backup settings", code="backup_error", status=500
        )
    log_event(
        "backup.toggle",
        "Backup settings updated",
        user_id=operator_id,
        context={"status": status},
    )
    return {"message": "Backup settings updated", "status": status}, 200


def resolve_backup_path(
    manager: BackupManager, filename: str, *, user_id: int | None
) -> Path:
    try:
        return manager.get_backup_path(filename, user_id=user_id)
    except ValueError:
        raise ValidationError(
            "Invalid backup filename", code="invalid_input", status=400
        )
    except FileNotFoundError:
        raise ValidationError("Backup not found", code="not_found", status=404)


def fetch_export_data(
    *,
    user_id: int,
    is_admin: bool,
    limit: int,
    offset: int,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], int, int]:
    stats_include_unassigned = False
    entries = backup_repo.get_export_entries(user_id, is_admin, limit, offset)
    activities = backup_repo.get_export_activities(user_id, is_admin, limit, offset)

    total_entries = backup_repo.count_export_entries(user_id, is_admin)
    total_activities = backup_repo.count_export_activities(user_id, is_admin)

    return entries, activities, int(total_entries), int(total_activities)  # type: ignore[arg-type]


def build_export_payload(
    *,
    user_id: int,
    is_admin: bool,
    limit: int,
    offset: int,
) -> Tuple[Dict[str, object], Dict[str, int]]:
    entries, activities, total_entries, total_activities = fetch_export_data(
        user_id=user_id,
        is_admin=is_admin,
        limit=limit,
        offset=offset,
    )
    payload = {
        "entries": entries,
        "activities": activities,
        "meta": {
            "entries": {"limit": limit, "offset": offset, "total": total_entries},
            "activities": {"limit": limit, "offset": offset, "total": total_activities},
        },
    }
    return payload, {
        "total_entries": total_entries,
        "total_activities": total_activities,
    }


def build_export_csv(entries, activities) -> str:
    return to_csv(entries, activities)
