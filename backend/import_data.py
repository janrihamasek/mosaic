import csv
from typing import Dict, Optional, Set, Tuple

from flask import has_app_context

from pydantic import ValidationError
from sqlalchemy import select

from extensions import db
from models import Activity, Entry, User
from schemas import CSVImportRow


def _ensure_activity(parsed: CSVImportRow, *, user_id: Optional[int]) -> Activity:
    session = db.session
    stmt = select(Activity).where(Activity.name == parsed.activity)
    activity = session.execute(stmt).scalar_one_or_none()

    if activity is None:
        payload: Dict[str, object] = {
            "name": parsed.activity,
            "category": parsed.category or "",
            "goal": parsed.goal,
            "description": parsed.description or "",
            "active": True,
            "frequency_per_day": parsed.frequency_per_day or 1,
            "frequency_per_week": parsed.frequency_per_week or 1,
            "deactivated_at": None,
            "user_id": user_id,
            "activity_type": "positive",
        }
        activity = Activity(**payload)
        session.add(activity)
        session.flush()
        return activity

    if user_id is not None and activity.user_id not in (None, user_id):
        raise ValueError(f"Activity '{parsed.activity}' already belongs to another user")

    if user_id is not None and activity.user_id is None:
        activity.user_id = user_id

    updated = False

    if parsed.category and parsed.category != (activity.category or ""):
        activity.category = parsed.category
        updated = True
    if parsed.description and parsed.description != (activity.description or ""):
        activity.description = parsed.description
        updated = True
    if parsed.goal is not None and float(activity.goal or 0) != float(parsed.goal):
        activity.goal = parsed.goal
        updated = True
    if parsed.frequency_per_day is not None and activity.frequency_per_day != parsed.frequency_per_day:
        activity.frequency_per_day = parsed.frequency_per_day
        updated = True
    if parsed.frequency_per_week is not None and activity.frequency_per_week != parsed.frequency_per_week:
        activity.frequency_per_week = parsed.frequency_per_week
        updated = True
    if not activity.active:
        activity.active = True
        activity.deactivated_at = None
        updated = True

    if updated:
        db.session.flush()

    return activity


def _upsert_entry(parsed: CSVImportRow, activity: Activity, *, user_id: Optional[int]) -> str:
    session = db.session
    stmt = select(Entry).where(Entry.date == parsed.date, Entry.activity == parsed.activity)
    if user_id is not None:
        stmt = stmt.where(Entry.user_id == user_id)
    entry = session.execute(stmt).scalar_one_or_none()

    activity_category = parsed.category or activity.category or ""
    activity_goal = parsed.goal if parsed.goal is not None else activity.goal or 0.0
    description = parsed.description or activity.description or ""
    entry_activity_type = getattr(activity, "activity_type", None) or "positive"

    if entry is None:
        payload: Dict[str, object] = {
            "date": parsed.date,
            "activity": parsed.activity,
            "description": description,
            "value": float(parsed.value),
            "note": parsed.note,
            "activity_category": activity_category,
            "activity_goal": activity_goal,
            "activity_type": entry_activity_type,
            "user_id": user_id,
        }
        entry = Entry(**payload)
        session.add(entry)
        return "created"

    if user_id is not None and entry.user_id is None:
        entry.user_id = user_id

    entry.value = float(parsed.value)
    entry.note = parsed.note
    entry.description = description
    entry.activity_category = activity_category
    entry.activity_goal = activity_goal
    entry.activity_type = entry_activity_type
    return "updated"


def _import_csv_impl(csv_path: str, *, commit: bool = True, user_id: Optional[int] = None) -> Dict[str, object]:
    created = 0
    updated = 0
    skipped = 0
    details: list[Dict[str, object]] = []
    seen_pairs: Set[Tuple[str, str]] = set()

    session = db.session

    try:
        with open(csv_path, newline="", encoding="utf-8") as csvfile:
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

                try:
                    activity = _ensure_activity(parsed, user_id=user_id)
                except ValueError as exc:
                    skipped += 1
                    details.append(
                        {
                            "row": index,
                            "date": parsed.date,
                            "activity": parsed.activity,
                            "status": "skipped",
                            "reason": str(exc),
                        }
                    )
                    continue

                status = _upsert_entry(parsed, activity, user_id=user_id)
                if status == "created":
                    _upsert_entry(parsed, activity, user_id=user_id)
                    created += 1
                else:
                    updated += 1

                details.append(
                    {
                        "row": index,
                        "date": parsed.date,
                        "activity": parsed.activity,
                        "status": status,
                    }
                )

        if commit:
            session.commit()
    except Exception:
        session.rollback()
        raise

    return {"created": created, "updated": updated, "skipped": skipped, "details": details}


def import_csv(csv_path: str, *, commit: bool = True, user_id: Optional[int] = None) -> Dict[str, object]:
    if has_app_context():
        return _import_csv_impl(csv_path, commit=commit, user_id=user_id)

    from app import app  # type: ignore circular import

    with app.app_context():
        return _import_csv_impl(csv_path, commit=commit, user_id=user_id)


__all__ = ["import_csv"]


if __name__ == "__main__":
    import argparse
    from app import app  # type: ignore

    parser = argparse.ArgumentParser(description="Import Mosaic activities and entries from CSV.")
    parser.add_argument("csv_path", help="Path to the CSV file.")
    parser.add_argument("--username", help="Username that should own imported data.")
    args = parser.parse_args()

    with app.app_context():
        owner_id: Optional[int] = None
        if args.username:
            owner_id = db.session.execute(select(User.id).where(User.username == args.username)).scalar_one_or_none()
            if owner_id is None:
                raise SystemExit(f"User '{args.username}' not found")
        result = import_csv(args.csv_path, user_id=owner_id)
    print(
        f"Import finished. Created: {result['created']}, "
        f"updated: {result['updated']}, skipped: {result['skipped']}"
    )
