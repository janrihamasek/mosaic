import csv
from typing import Any, Dict, List, Optional, Set, Tuple

from flask import has_app_context
from pydantic import ValidationError
from repositories import entries_repo, users_repo
from schemas import CSVImportRow


def _import_csv_impl(
    csv_path: str, *, commit: bool = True, user_id: Optional[int] = None
) -> Dict[str, object]:
    _ = commit  # retained for compatibility with previous signature
    created = 0
    updated = 0
    skipped = 0
    details: List[Dict[str, object]] = []
    seen_pairs: Set[Tuple[str, str]] = set()
    parsed_rows: List[Dict[str, Any]] = []

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

            parsed_dict: Dict[str, Any] = parsed.model_dump()
            parsed_dict["row"] = index
            parsed_rows.append(parsed_dict)

    created_rows, updated_rows, repo_skipped, repo_details = (
        entries_repo.import_entries_from_rows(parsed_rows, user_id)
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
    }


def import_csv(
    csv_path: str, *, commit: bool = True, user_id: Optional[int] = None
) -> Dict[str, object]:
    if has_app_context():
        return _import_csv_impl(csv_path, commit=commit, user_id=user_id)

    from app import app  # type: ignore circular import

    with app.app_context():
        return _import_csv_impl(csv_path, commit=commit, user_id=user_id)


__all__ = ["import_csv"]


if __name__ == "__main__":
    import argparse

    from app import app  # type: ignore

    parser = argparse.ArgumentParser(
        description="Import Mosaic activities and entries from CSV."
    )
    parser.add_argument("csv_path", help="Path to the CSV file.")
    parser.add_argument("--username", help="Username that should own imported data.")
    args = parser.parse_args()

    with app.app_context():
        owner_id: Optional[int] = None
        if args.username:
            owner = users_repo.get_user_by_username(args.username)
            owner_id = owner["id"] if owner and "id" in owner else None
            if owner_id is None:
                raise SystemExit(f"User '{args.username}' not found")
        result = import_csv(args.csv_path, user_id=owner_id)
    print(
        f"Import finished. Created: {result['created']}, "
        f"updated: {result['updated']}, skipped: {result['skipped']}"
    )
