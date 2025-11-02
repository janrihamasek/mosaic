import sqlite3
from pathlib import Path

import pytest

from app import app
from import_data import import_csv


def _write_csv(tmp_path, name, rows):
    header = "date,activity,value,note,description,category,goal\n"
    content = header + "\n".join(rows) + "\n"
    path = tmp_path / name
    path.write_text(content, encoding="utf-8")
    return path


@pytest.mark.usefixtures("client")
def test_import_csv_skips_duplicate_rows(tmp_path):
    csv_path = _write_csv(
        tmp_path,
        "duplicates.csv",
        [
            "2024-03-01,Swim,2,,Morning swim,Fitness,12",
            "2024-03-01,Swim,3,,Evening swim,Fitness,12",
        ],
    )

    summary = import_csv(str(csv_path), db_path=app.config["DB_PATH"])

    assert summary["created"] == 1
    assert summary["skipped"] == 1
    reasons = {detail.get("reason") for detail in summary["details"] if detail["status"] == "skipped"}
    assert "duplicate_in_file" in reasons

    conn = sqlite3.connect(app.config["DB_PATH"])
    try:
        row = conn.execute(
            "SELECT value, note FROM entries WHERE date = ? AND activity = ?",
            ("2024-03-01", "Swim"),
        ).fetchone()
        assert row is not None
        assert pytest.approx(row[0]) == 2.0
        assert row[1] == ""
    finally:
        conn.close()


@pytest.mark.usefixtures("client")
def test_import_csv_flags_missing_required_fields(tmp_path):
    csv_path = _write_csv(
        tmp_path,
        "missing.csv",
        [
            ",Yoga,1,,Stretching,Wellness,3",
            "2024-03-02,,1,,Stretching,Wellness,3",
        ],
    )

    summary = import_csv(str(csv_path), db_path=app.config["DB_PATH"])

    assert summary["created"] == 0
    assert summary["skipped"] == 2
    reasons = [detail.get("reason") for detail in summary["details"]]
    assert any("date is required" in reason for reason in reasons)
    assert any("activity is required" in reason for reason in reasons)

    conn = sqlite3.connect(app.config["DB_PATH"])
    try:
        total = conn.execute("SELECT COUNT(*) FROM entries").fetchone()[0]
        assert total == 0
    finally:
        conn.close()


@pytest.mark.usefixtures("client")
def test_import_csv_updates_existing_and_creates_new(tmp_path):
    db_path = Path(app.config["DB_PATH"])

    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            INSERT INTO activities (name, category, goal, description, active, frequency_per_day, frequency_per_week, deactivated_at)
            VALUES (?, ?, ?, ?, 1, ?, ?, NULL)
            """,
            ("Run", "Health", 10.0, "Jogging", 1, 7),
        )
        conn.execute(
            """
            INSERT INTO entries (date, activity, description, value, note, activity_category, activity_goal)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            ("2024-03-01", "Run", "Jogging", 5.0, "Existing note", "Health", 10.0),
        )
        conn.commit()
    finally:
        conn.close()

    csv_path = _write_csv(
        tmp_path,
        "mixed.csv",
        [
            "2024-03-01,Run,8,Updated note,Jogging,Health,10",
            "02/03/2024,Reading,1,,Evening reading,Leisure,7",
        ],
    )

    summary = import_csv(str(csv_path), db_path=str(db_path))

    assert summary["created"] == 1
    assert summary["updated"] == 1
    assert summary["skipped"] == 0

    conn = sqlite3.connect(db_path)
    try:
        updated_row = conn.execute(
            "SELECT value, note FROM entries WHERE date = ? AND activity = ?",
            ("2024-03-01", "Run"),
        ).fetchone()
        assert updated_row is not None
        assert pytest.approx(updated_row[0]) == 8.0
        assert updated_row[1] == "Updated note"

        created_row = conn.execute(
            "SELECT date, activity, activity_category, activity_goal FROM entries WHERE activity = ?",
            ("Reading",),
        ).fetchone()
        assert created_row is not None
        assert created_row[0] == "2024-03-02"
        assert created_row[2] == "Leisure"
        assert pytest.approx(created_row[3]) == 7.0
    finally:
        conn.close()
