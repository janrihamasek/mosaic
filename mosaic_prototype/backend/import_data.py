import csv
from typing import Dict, Set, Tuple

from flask import has_app_context

from pydantic import ValidationError
from sqlalchemy import select

from extensions import db
from models import Activity, Entry
from schemas import CSVImportRow


def _ensure_activity(parsed: CSVImportRow) -> Activity:
    session = db.session
    stmt = select(Activity).where(Activity.name == parsed.activity)
    activity = session.execute(stmt).scalar_one_or_none()

    if activity is None:
        activity = Activity(
            name=parsed.activity,
            category=parsed.category or "",
            goal=parsed.goal,
            description=parsed.description or "",
            active=True,
            frequency_per_day=parsed.frequency_per_day or 1,
            frequency_per_week=parsed.frequency_per_week or 1,
            deactivated_at=None,
        )
        session.add(activity)
        session.flush()
        return activity

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


def _upsert_entry(parsed: CSVImportRow, activity: Activity) -> str:
    session = db.session
    stmt = select(Entry).where(Entry.date == parsed.date, Entry.activity == parsed.activity)
    entry = session.execute(stmt).scalar_one_or_none()

    activity_category = parsed.category or activity.category or ""
    activity_goal = parsed.goal if parsed.goal is not None else activity.goal or 0.0
    description = parsed.description or activity.description or ""

    if entry is None:
        entry = Entry(
            date=parsed.date,
            activity=parsed.activity,
            description=description,
            value=float(parsed.value),
            note=parsed.note,
            activity_category=activity_category,
            activity_goal=activity_goal,
        )
        session.add(entry)
        return "created"

    entry.value = float(parsed.value)
    entry.note = parsed.note
    entry.description = description
    entry.activity_category = activity_category
    entry.activity_goal = activity_goal
    return "updated"


def _import_csv_impl(csv_path: str, *, commit: bool = True) -> Dict[str, object]:
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
                            "raw": row,
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

                activity = _ensure_activity(parsed)
                status = _upsert_entry(parsed, activity)
                if status == "created":
                    _upsert_entry(parsed, activity)

                if status == "created":
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


def import_csv(csv_path: str, *, commit: bool = True) -> Dict[str, object]:
    if has_app_context():
        return _import_csv_impl(csv_path, commit=commit)

    from app import app  # type: ignore circular import

    with app.app_context():
        return _import_csv_impl(csv_path, commit=commit)


__all__ = ["import_csv"]


if __name__ == "__main__":
    import argparse
    from app import app  # type: ignore

    parser = argparse.ArgumentParser(description="Import Mosaic activities and entries from CSV.")
    parser.add_argument("csv_path", help="Path to the CSV file.")
    args = parser.parse_args()

    with app.app_context():
        result = import_csv(args.csv_path)
    print(
        f"Import finished. Created: {result['created']}, "
        f"updated: {result['updated']}, skipped: {result['skipped']}"
    )
