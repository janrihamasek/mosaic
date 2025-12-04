import csv
from typing import Any, Dict, List, Optional, Set, Tuple

from flask import has_app_context
from pydantic import ValidationError
from db_utils import transactional_connection
from extensions import db
from repositories import entries_repo, users_repo
from schemas import CSVActivityImportRow, CSVImportRow
from services.backup_serializers import ACTIVITY_FIELDS, ENTRY_FIELDS


def _import_csv_impl(
    csv_path: str, *, dry_run: bool = False, user_id: int
) -> Dict[str, object]:
    created = 0
    updated = 0
    skipped = 0
    details: List[Dict[str, object]] = []
    seen_pairs: Set[Tuple[str, str]] = set()
    parsed_rows: List[Dict[str, Any]] = []
    activity_rows: List[Dict[str, Any]] = []
    seen_activity_names: Set[str] = set()

    with open(csv_path, newline="", encoding="utf-8") as csvfile:
        peek = csvfile.readline()
        csvfile.seek(0)
        if peek.lower().startswith("dataset,"):
            # Export/backup format: entries section + activities section with their own headers.
            reader = csv.reader(csvfile)
            mode: Optional[str] = None
            for line_number, row in enumerate(reader, start=1):
                if not row or not any((value or "").strip() for value in row):
                    mode = None
                    continue
                first_cell = (row[0] or "").strip().lower()
                if first_cell == "dataset":
                    if len(row) > 1 and (row[1] or "").strip().lower() == "entry_id":
                        mode = "entries"
                    elif len(row) > 1 and (row[1] or "").strip().lower() == "activity_id":
                        mode = "activities"
                    else:
                        mode = None
                    continue

                if mode == "entries":
                    # Map row values to ENTRY_FIELDS order.
                    values = list(row[1:]) + [""] * (len(ENTRY_FIELDS) - len(row[1:]))
                    raw_entry = dict(zip(ENTRY_FIELDS, values))
                    entry_row = {
                        "date": raw_entry.get("date"),
                        "activity": raw_entry.get("activity"),
                        "description": raw_entry.get("entry_description") or "",
                        "value": raw_entry.get("value"),
                        "note": raw_entry.get("note") or "",
                        "category": raw_entry.get("activity_category") or "",
                        "goal": raw_entry.get("activity_goal") or 0,
                        "activity_type": raw_entry.get("activity_type") or "positive",
                    }
                    try:
                        parsed = CSVImportRow.model_validate(entry_row)
                    except ValidationError as exc:
                        message = exc.errors()[0].get("msg", "Invalid row")
                        skipped += 1
                        details.append(
                            {
                                "row": line_number,
                                "status": "skipped",
                                "reason": message,
                                "raw": entry_row,
                            }
                        )
                        continue
                    key = (parsed.date, parsed.activity.lower())
                    if key in seen_pairs:
                        skipped += 1
                        details.append(
                            {
                                "row": line_number,
                                "date": parsed.date,
                                "activity": parsed.activity,
                                "status": "skipped",
                                "reason": "duplicate_in_file",
                            }
                        )
                        continue
                    seen_pairs.add(key)
                    parsed_dict: Dict[str, Any] = parsed.model_dump()
                    parsed_dict["row"] = line_number
                    parsed_rows.append(parsed_dict)
                elif mode == "activities":
                    values = list(row[1:]) + [""] * (len(ACTIVITY_FIELDS) - len(row[1:]))
                    raw_activity = dict(zip(ACTIVITY_FIELDS, values))
                    activity_row: Dict[str, Any] = {
                        "name": raw_activity.get("name"),
                        "category": raw_activity.get("category"),
                        "activity_type": raw_activity.get("activity_type"),
                        "goal": raw_activity.get("goal"),
                        "description": raw_activity.get("activity_description"),
                        "active": raw_activity.get("active"),
                        "frequency_per_day": raw_activity.get("frequency_per_day"),
                        "frequency_per_week": raw_activity.get("frequency_per_week"),
                        "deactivated_at": raw_activity.get("deactivated_at"),
                    }
                    try:
                        parsed_activity = CSVActivityImportRow.model_validate(
                            activity_row
                        )
                    except ValidationError as exc:
                        message = exc.errors()[0].get("msg", "Invalid activity row")
                        details.append(
                            {
                                "row": line_number,
                                "dataset": "activities",
                                "status": "skipped",
                                "reason": message,
                                "raw": activity_row,
                            }
                        )
                        continue
                    name_key = parsed_activity.name.lower()
                    if name_key in seen_activity_names:
                        details.append(
                            {
                                "row": line_number,
                                "dataset": "activities",
                                "name": parsed_activity.name,
                                "status": "skipped",
                                "reason": "duplicate_activity_in_file",
                            }
                        )
                        continue
                    seen_activity_names.add(name_key)
                    parsed_activity_dict = parsed_activity.model_dump()
                    parsed_activity_dict["row"] = line_number
                    activity_rows.append(parsed_activity_dict)
                else:
                    continue
        else:
            reader = csv.DictReader(csvfile)
            if reader.fieldnames is None:
                raise ValueError("CSV file is missing a header row")

            for index, row in enumerate(reader, start=2):
                if not row or not any((value or "").strip() for value in row.values()):
                    continue

                try:
                    parsed = CSVImportRow.model_validate(row)
                except ValidationError as exc:
                    message = exc.errors()[0].get("msg", "Invalid row")
                    skipped += 1
                    details.append(
                        {
                            "row": index,
                            "status": "skipped",
                            "reason": message,
                            "raw": {str(key or ""): value for key, value in row.items()},
                        }
                    )
                    continue

                key = (parsed.date, parsed.activity.lower())
                if key in seen_pairs:
                    skipped += 1
                    details.append(
                        {
                            "row": index,
                            "date": parsed.date,
                            "activity": parsed.activity,
                            "status": "skipped",
                            "reason": "duplicate_in_file",
                        }
                    )
                    continue
                seen_pairs.add(key)

                parsed_dict: Dict[str, Any] = parsed.model_dump()
                parsed_dict["row"] = index
                parsed_rows.append(parsed_dict)

    if activity_rows and not dry_run:
        with transactional_connection(db.engine) as conn:
            for activity_row in activity_rows:
                try:
                    status = _upsert_activity_from_export(activity_row, user_id, conn)
                    details.append(
                        {
                            "row": activity_row.get("row"),
                            "dataset": "activities",
                            "name": activity_row.get("name"),
                            "status": status,
                        }
                    )
                except Exception as exc:  # pragma: no cover - defensive
                    details.append(
                        {
                            "row": activity_row.get("row"),
                            "dataset": "activities",
                            "name": activity_row.get("name"),
                            "status": "skipped",
                            "reason": str(exc),
                        }
                    )

    locked_activity_names = {row["name"].lower() for row in activity_rows}

    created_rows, updated_rows, repo_skipped, repo_details = (
        entries_repo.import_entries_from_rows_dry_run(
            parsed_rows,
            user_id,
            locked_activity_names=locked_activity_names,
        )
        if dry_run
        else entries_repo.import_entries_from_rows(
            parsed_rows,
            user_id,
            locked_activity_names=locked_activity_names,
        )
    )
    created += created_rows
    updated += updated_rows
    skipped += repo_skipped
    details.extend(repo_details)

    return {
        "created": created,
        "updated": updated,
        "skipped": skipped,
        "details": details,
        "dry_run": dry_run,
    }


def _upsert_activity_from_export(row: Dict[str, Any], user_id: int, conn) -> str:
    """
    Upsert an activity row coming from an export/backup dataset.
    """
    name = row["name"]
    category = row.get("category") or ""
    activity_type = (row.get("activity_type") or "positive").lower()
    goal = float(row.get("goal") or 0)
    description = row.get("description") or ""
    active_value = row.get("active")
    active = (
        active_value
        if isinstance(active_value, bool)
        else str(active_value or "").strip().lower() in ("1", "true", "yes", "y", "t")
    )
    frequency_per_day = int(row.get("frequency_per_day") or 1)
    frequency_per_week = int(row.get("frequency_per_week") or 1)
    deactivated_at_raw = row.get("deactivated_at")
    deactivated_at = (
        None
        if deactivated_at_raw in (None, "")
        else str(deactivated_at_raw).strip()
    )
    existing = conn.execute(
        "SELECT id FROM activities WHERE name = ? AND user_id = ?",
        (name, user_id),
    ).fetchone()
    if existing:
        conn.execute(
            """
            UPDATE activities
               SET category = ?,
                   activity_type = ?,
                   goal = ?,
                   description = ?,
                   active = ?,
                   frequency_per_day = ?,
                   frequency_per_week = ?,
                   deactivated_at = ?
             WHERE id = ? AND user_id = ?
            """,
            (
                category,
                activity_type,
                goal,
                description,
                active,
                frequency_per_day,
                frequency_per_week,
                deactivated_at,
                existing["id"],
                user_id,
            ),
        )
        return "updated"

    conn.execute(
        """
        INSERT INTO activities (
            name,
            category,
            activity_type,
            goal,
            description,
            active,
            frequency_per_day,
            frequency_per_week,
            deactivated_at,
            user_id
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            name,
            category,
            activity_type,
            goal,
            description,
            active,
            frequency_per_day,
            frequency_per_week,
            deactivated_at,
            user_id,
        ),
    )
    return "created"


def import_csv(
    csv_path: str, *, dry_run: bool = False, user_id: Optional[int] = None
) -> Dict[str, object]:
    if user_id is None:
        raise ValueError("user_id is required for CSV import")
    if has_app_context():
        return _import_csv_impl(csv_path, dry_run=dry_run, user_id=user_id)

    from app import app  # type: ignore circular import

    with app.app_context():
        return _import_csv_impl(csv_path, dry_run=dry_run, user_id=user_id)


__all__ = ["import_csv"]


if __name__ == "__main__":
    import argparse

    from app import app  # type: ignore

    parser = argparse.ArgumentParser(
        description="Import Mosaic activities and entries from CSV."
    )
    parser.add_argument("csv_path", help="Path to the CSV file.")
    parser.add_argument(
        "--username",
        required=True,
        help="Username that should own imported data (required).",
    )
    args = parser.parse_args()

    with app.app_context():
        owner = users_repo.get_user_by_username(args.username)
        owner_id = owner["id"] if owner and "id" in owner else None
        if owner_id is None:
            raise SystemExit(f"User '{args.username}' not found")
        result = import_csv(args.csv_path, user_id=owner_id)
    print(
        f"Import finished. Created: {result['created']}, "
        f"updated: {result['updated']}, skipped: {result['skipped']}"
    )
