"""
Shared serializers for backup/export payloads to keep JSON/CSV schemas aligned.
"""

import csv
import io
from typing import Iterable, List, Sequence

# Canonical field ordering for entries and activities
ENTRY_FIELDS: Sequence[str] = [
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

ACTIVITY_FIELDS: Sequence[str] = [
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


def to_csv(entries: Iterable[dict], activities: Iterable[dict]) -> str:
    """Render entries + activities into a single CSV string with consistent schema."""
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(["dataset", *ENTRY_FIELDS])
    for entry in entries:
        writer.writerow(["entries", *[entry.get(field) for field in ENTRY_FIELDS]])

    writer.writerow([])  # separator

    writer.writerow(["dataset", *ACTIVITY_FIELDS])
    for activity in activities:
        writer.writerow(
            ["activities", *[activity.get(field) for field in ACTIVITY_FIELDS]]
        )

    return output.getvalue()
