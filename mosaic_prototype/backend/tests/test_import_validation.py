import pytest
from sqlalchemy import func, select

from app import app
from extensions import db
from import_data import import_csv
from models import Activity, Entry


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

    summary = import_csv(str(csv_path))

    assert summary["created"] == 1
    assert summary["skipped"] == 1
    reasons = {detail.get("reason") for detail in summary["details"] if detail["status"] == "skipped"}
    assert "duplicate_in_file" in reasons

    with app.app_context():
        row = db.session.execute(
            select(Entry.value, Entry.note).where(Entry.date == "2024-03-01", Entry.activity == "Swim")
        ).first()
        assert row is not None
        assert pytest.approx(row.value) == 2.0
        assert row.note == ""


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

    summary = import_csv(str(csv_path))

    assert summary["created"] == 0
    assert summary["skipped"] == 2
    reasons = [detail.get("reason") for detail in summary["details"]]
    assert any("date is required" in reason for reason in reasons)
    assert any("activity is required" in reason for reason in reasons)

    with app.app_context():
        total = db.session.execute(select(func.count()).select_from(Entry)).scalar()
        assert total == 0


@pytest.mark.usefixtures("client")
def test_import_csv_updates_existing_and_creates_new(tmp_path):
    with app.app_context():
        activity = Activity(
            name="Run",
            category="Health",
            goal=10.0,
            description="Jogging",
            active=True,
            frequency_per_day=1,
            frequency_per_week=7,
            deactivated_at=None,
        )
        db.session.add(activity)
        db.session.flush()
        entry = Entry(
            date="2024-03-01",
            activity="Run",
            description="Jogging",
            value=5.0,
            note="Existing note",
            activity_category="Health",
            activity_goal=10.0,
        )
        db.session.add(entry)
        db.session.commit()

    csv_path = _write_csv(
        tmp_path,
        "mixed.csv",
        [
            "2024-03-01,Run,8,Updated note,Jogging,Health,10",
            "02/03/2024,Reading,1,,Evening reading,Leisure,7",
        ],
    )

    summary = import_csv(str(csv_path))

    assert summary["created"] == 1
    assert summary["updated"] == 1
    assert summary["skipped"] == 0

    with app.app_context():
        updated_row = db.session.execute(
            select(Entry.value, Entry.note).where(Entry.date == "2024-03-01", Entry.activity == "Run")
        ).first()
        assert updated_row is not None
        assert pytest.approx(updated_row.value) == 8.0
        assert updated_row.note == "Updated note"

        created_row = db.session.execute(
            select(Entry.date, Entry.activity_category, Entry.activity_goal).where(Entry.activity == "Reading")
        ).first()
        assert created_row is not None
        assert created_row.date == "2024-03-02"
        assert created_row.activity_category == "Leisure"
        assert pytest.approx(created_row.activity_goal) == 7.0
