"""
Backup service.

Wraps backup scheduling, status reporting, toggling, and export helpers without
any Flask HTTP dependencies.
"""

import csv
import io
from pathlib import Path
from typing import Dict, Tuple, List, Any

from backup_manager import BackupManager
from audit import log_event
from security import ValidationError
from .common import get_db_connection


def get_backup_status(manager: BackupManager) -> Dict:
    try:
        return manager.get_status()
    except Exception as exc:
        raise ValidationError(str(exc), code="backup_error", status=500)


def run_backup(manager: BackupManager, *, operator_id: int | None) -> Tuple[Dict[str, object], int]:
    try:
        result = manager.create_backup(initiated_by="api")
    except Exception as exc:
        log_event(
            "backup.run_failed",
            "Backup creation failed",
            user_id=operator_id,
            level="error",
            context={"error": str(exc)},
        )
        raise ValidationError("Failed to create backup", code="backup_error", status=500)
    log_event(
        "backup.run",
        "Backup created",
        user_id=operator_id,
        context={"backup": result},
    )
    return {"message": "Backup completed", "backup": result}, 200


def toggle_backup(manager: BackupManager, *, operator_id: int | None, payload: Dict[str, object]) -> Tuple[Dict[str, object], int]:
    enabled = payload.get("enabled")
    interval = payload.get("interval_minutes")

    if enabled is not None and not isinstance(enabled, bool):
        raise ValidationError("enabled must be a boolean", code="invalid_input", status=400)
    if interval is not None:
        try:
            interval = int(interval)
        except (TypeError, ValueError):
            raise ValidationError("interval_minutes must be an integer", code="invalid_input", status=400)
        if interval < 5:
            raise ValidationError("interval_minutes must be at least 5", code="invalid_input", status=400)

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
        raise ValidationError("Unable to update backup settings", code="backup_error", status=500)
    log_event(
        "backup.toggle",
        "Backup settings updated",
        user_id=operator_id,
        context={"status": status},
    )
    return {"message": "Backup settings updated", "status": status}, 200


def resolve_backup_path(manager: BackupManager, filename: str) -> Path:
    try:
        return manager.get_backup_path(filename)
    except ValueError:
        raise ValidationError("Invalid backup filename", code="invalid_input", status=400)
    except FileNotFoundError:
        raise ValidationError("Backup not found", code="not_found", status=404)


def _user_scope_clause(column: str, *, include_unassigned: bool = False) -> str:
    clause = f"{column} = ?"
    if include_unassigned:
        clause = f"({clause} OR {column} IS NULL)"
    return clause


def fetch_export_data(
    *,
    user_id: int,
    is_admin: bool,
    limit: int,
    offset: int,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], int, int]:
    stats_include_unassigned = False
    conn = get_db_connection()
    try:
        entry_params: list = []
        entry_where = ""
        if user_id is not None:
            entry_where = f"WHERE {_user_scope_clause('e.user_id', include_unassigned=is_admin)}"
            entry_params.append(user_id)

        entries_cursor = conn.execute(
            f"""
            SELECT
                e.id AS entry_id,
                e.date,
                e.activity,
                e.description AS entry_description,
                e.value,
                e.note,
                e.activity_category,
                e.activity_goal,
                e.activity_type
            FROM entries e
            LEFT JOIN activities a
              ON a.name = e.activity
             AND (a.user_id = e.user_id OR a.user_id IS NULL)
            {entry_where}
            ORDER BY e.date ASC, e.id ASC
            LIMIT ? OFFSET ?
            """,
            tuple(entry_params + [limit, offset]),
        )

        activity_params: list = []
        activity_where = ""
        if user_id is not None:
            activity_where = f"WHERE {_user_scope_clause('a.user_id', include_unassigned=is_admin)}"
            activity_params.append(user_id)

        activities_cursor = conn.execute(
            f"""
            SELECT
                a.id AS activity_id,
                a.name,
                a.category,
                a.activity_type,
                a.goal,
                a.description AS activity_description,
                a.active,
                a.frequency_per_day,
                a.frequency_per_week,
                a.deactivated_at
            FROM activities a
            {activity_where}
            ORDER BY a.name ASC, a.id ASC
            LIMIT ? OFFSET ?
            """,
            tuple(activity_params + [limit, offset]),
        )

        if user_id is None:
            total_entries_stmt = "SELECT COUNT(1) FROM entries"
            total_entries_params: Tuple = ()
            total_activities_stmt = "SELECT COUNT(1) FROM activities"
            total_activities_params: Tuple = ()
        else:
            total_entries_stmt = f"SELECT COUNT(1) FROM entries WHERE {_user_scope_clause('user_id', include_unassigned=is_admin)}"
            total_entries_params = (user_id,)
            total_activities_stmt = f"SELECT COUNT(1) FROM activities WHERE {_user_scope_clause('user_id', include_unassigned=is_admin)}"
            total_activities_params = (user_id,)

        total_entries = conn.execute(total_entries_stmt, total_entries_params).scalar_one()
        total_activities = conn.execute(total_activities_stmt, total_activities_params).scalar_one()
        entries = [dict(row) for row in entries_cursor.fetchall()]
        activities = [dict(row) for row in activities_cursor.fetchall()]
        return entries, activities, int(total_entries), int(total_activities)
    finally:
        conn.close()


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
    return payload, {"total_entries": total_entries, "total_activities": total_activities}


def build_export_csv(entries, activities) -> str:
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(
        [
            "dataset",
            "entry_id",
            "date",
            "activity",
            "entry_description",
            "value",
            "note",
            "activity_category",
            "activity_goal",
            "activity_type",
        ]
    )
    for entry in entries:
        writer.writerow(
            [
                "entries",
                entry.get("entry_id"),
                entry.get("date"),
                entry.get("activity"),
                entry.get("entry_description"),
                entry.get("value"),
                entry.get("note"),
                entry.get("activity_category"),
                entry.get("activity_goal"),
                entry.get("activity_type"),
            ]
        )

    writer.writerow([])
    writer.writerow(
        [
            "dataset",
            "activity_id",
            "name",
            "category",
            "activity_type",
            "goal",
            "activity_description",
            "active",
            "frequency_per_day",
            "frequency_per_week",
            "deactivated_at",
        ]
    )
    for activity in activities:
        writer.writerow(
            [
                "activities",
                activity.get("activity_id"),
                activity.get("name"),
                activity.get("category"),
                activity.get("activity_type"),
                activity.get("goal"),
                activity.get("activity_description"),
                activity.get("active"),
                activity.get("frequency_per_day"),
                activity.get("frequency_per_week"),
                activity.get("deactivated_at"),
            ]
        )

    return output.getvalue()
