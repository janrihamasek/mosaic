import csv
import io

from services.backup_serializers import to_csv


def test_to_csv_renders_entries_and_activities():
    entries = [
        {
            "entry_id": 1,
            "date": "2024-05-01",
            "activity": "Reading",
            "entry_description": "Read",
            "value": 1,
            "note": "",
            "activity_category": "Books",
            "activity_goal": 5,
            "activity_type": "positive",
        }
    ]
    activities = [
        {
            "activity_id": 10,
            "name": "Reading",
            "category": "Books",
            "activity_type": "negative",
            "goal": 2.5,
            "activity_description": "Rest more",
            "active": False,
            "frequency_per_day": 1,
            "frequency_per_week": 3,
            "deactivated_at": "2024-06-15",
        }
    ]

    csv_text = to_csv(entries, activities)
    reader = csv.reader(io.StringIO(csv_text))

    rows = list(reader)
    # entries header + one entry row + blank separator + activities header + one activity row
    assert rows[0][:4] == ["dataset", "entry_id", "date", "activity"]
    assert rows[1][0] == "entries"
    assert rows[1][1] == "1"
    assert rows[1][3] == "Reading"
    # separator is empty row
    assert rows[2] == []
    assert rows[3][:3] == ["dataset", "activity_id", "name"]
    assert rows[4][0] == "activities"
    assert rows[4][1] == "10"
    assert rows[4][2] == "Reading"
    assert rows[4][4] == "negative"
    # active, frequency_per_day, frequency_per_week, deactivated_at
    assert rows[4][7] in ("False", "false", "0", "False") or rows[4][7] is False
    assert rows[4][8] == "1"
    assert rows[4][9] == "3"
    assert rows[4][10] == "2024-06-15"
