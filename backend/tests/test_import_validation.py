from pathlib import Path
from typing import Any, Dict, List, Sequence, cast

import pytest
from app import app
from extensions import db
from import_data import import_csv
from models import Activity, Entry, User
from sqlalchemy import func, select


def _write_csv(tmp_path, name: str, rows: Sequence[str]) -> Path:
    header = "date,activity,value,note,description,category,goal\n"
    content = header + "\n".join(rows) + "\n"
    path = tmp_path / name
    path.write_text(content, encoding="utf-8")
    return path


@pytest.mark.usefixtures("client")
def test_import_csv_skips_duplicate_rows(tmp_path):
    with app.app_context():
        user = User(username="import_duplicates", password_hash="x")
        db.session.add(user)
        db.session.commit()
        user_id = user.id

    csv_path = _write_csv(
        tmp_path,
        "duplicates.csv",
        [
            "2024-03-01,Swim,2,,Morning swim,Fitness,12",
            "2024-03-01,Swim,3,,Evening swim,Fitness,12",
        ],
    )

    summary: Dict[str, Any] = import_csv(str(csv_path), user_id=user_id)

    assert summary["created"] == 1
    assert summary["skipped"] == 1
    details = cast(List[Dict[str, Any]], summary["details"])
    reasons = {
        detail.get("reason") for detail in details if detail["status"] == "skipped"
    }
    assert "duplicate_in_file" in reasons

    with app.app_context():
        row = db.session.execute(
            select(Entry.value, Entry.note).where(
                Entry.date == "2024-03-01",
                Entry.activity == "Swim",
                Entry.user_id == user_id,
            )
        ).first()
        assert row is not None
        assert pytest.approx(row.value) == 2.0
        assert row.note == ""


@pytest.mark.usefixtures("client")
def test_import_csv_flags_missing_required_fields(tmp_path):
    with app.app_context():
        user = User(username="import_missing", password_hash="x")
        db.session.add(user)
        db.session.commit()
        user_id = user.id

    csv_path = _write_csv(
        tmp_path,
        "missing.csv",
        [
            ",Yoga,1,,Stretching,Wellness,3",
            "2024-03-02,,1,,Stretching,Wellness,3",
        ],
    )

    summary = cast(Dict[str, Any], import_csv(str(csv_path), user_id=user_id))

    assert summary["created"] == 0
    assert summary["skipped"] == 2
    details = cast(List[Dict[str, Any]], summary["details"])
    reasons = [detail.get("reason") or "" for detail in details]
    assert any("date is required" in reason for reason in reasons)
    assert any("activity is required" in reason for reason in reasons)

    with app.app_context():
        total = db.session.execute(
            select(func.count()).select_from(Entry).where(Entry.user_id == user_id)
        ).scalar()
        assert total == 0


@pytest.mark.usefixtures("client")
def test_import_csv_updates_existing_and_creates_new(tmp_path):
    with app.app_context():
        user = User(username="import_updates", password_hash="x")
        db.session.add(user)
        db.session.flush()

        activity_payload: Dict[str, Any] = {
            "name": "Run",
            "category": "Health",
            "goal": 10.0,
            "description": "Jogging",
            "active": True,
            "frequency_per_day": 1,
            "frequency_per_week": 7,
            "deactivated_at": None,
            "user_id": user.id,
        }
        activity = Activity(**activity_payload)
        db.session.add(activity)
        db.session.flush()
        entry_payload: Dict[str, Any] = {
            "date": "2024-03-01",
            "activity": "Run",
            "description": "Jogging",
            "value": 5.0,
            "note": "Existing note",
            "activity_category": "Health",
            "activity_goal": 10.0,
            "user_id": user.id,
        }
        entry = Entry(**entry_payload)
        db.session.add(entry)
        db.session.commit()
        user_id = user.id

    csv_path = _write_csv(
        tmp_path,
        "mixed.csv",
        [
            "2024-03-01,Run,8,Updated note,Jogging,Health,10",
            "02/03/2024,Reading,1,,Evening reading,Leisure,7",
        ],
    )

    summary = cast(Dict[str, Any], import_csv(str(csv_path), user_id=user_id))

    assert summary["created"] == 1
    assert summary["updated"] == 1
    assert summary["skipped"] == 0

    with app.app_context():
        updated_row = db.session.execute(
            select(Entry.value, Entry.note).where(
                Entry.date == "2024-03-01",
                Entry.activity == "Run",
                Entry.user_id == user_id,
            )
        ).first()
        assert updated_row is not None
        assert pytest.approx(updated_row.value) == 8.0
        assert updated_row.note == "Updated note"

        created_row = db.session.execute(
            select(Entry.date, Entry.activity_category, Entry.activity_goal).where(
                Entry.activity == "Reading", Entry.user_id == user_id
            )
        ).first()
        assert created_row is not None
        assert created_row.date == "2024-03-02"
        assert created_row.activity_category == "Leisure"
        assert pytest.approx(created_row.activity_goal) == 7.0


@pytest.mark.usefixtures("client")
def test_import_csv_dry_run_does_not_persist(tmp_path):
    with app.app_context():
        user = User(username="import_dry", password_hash="x")
        db.session.add(user)
        db.session.commit()
        user_id = user.id

    csv_path = _write_csv(
        tmp_path,
        "dry_run.csv",
        [
            "2024-03-05,Swim,1,,Notes,Fitness,5",
        ],
    )

    summary = cast(Dict[str, Any], import_csv(str(csv_path), dry_run=True, user_id=user_id))

    assert summary["dry_run"] is True
    assert summary["created"] == 1
    assert summary["updated"] == 0
    assert summary["skipped"] == 0

    with app.app_context():
        total_entries = db.session.execute(
            select(func.count()).select_from(Entry).where(Entry.user_id == user_id)
        ).scalar()
        assert total_entries == 0


@pytest.mark.usefixtures("client")
def test_import_csv_uses_activity_dataset(tmp_path):
    with app.app_context():
        user = User(username="import_activity_dataset", password_hash="x")
        db.session.add(user)
        db.session.commit()
        user_id = user.id

    csv_content = "\n".join(
        [
            "dataset,entry_id,date,activity,entry_description,value,note,activity_category,activity_goal,activity_type",
            "entries,,2024-05-01,Reading,Reading entry,1,,Books,5,positive",
            "",
            "dataset,activity_id,name,category,activity_type,goal,activity_description,active,frequency_per_day,frequency_per_week,deactivated_at",
            "activities,,Reading,Books,negative,2.5,Should rest,false,2,3,2024-05-10",
        ]
    )
    csv_path = tmp_path / "export_with_activities.csv"
    csv_path.write_text(csv_content, encoding="utf-8")

    summary = import_csv(str(csv_path), user_id=user_id)
    assert summary["created"] == 1

    with app.app_context():
        activity = db.session.execute(
            select(Activity).where(
                Activity.user_id == user_id, Activity.name == "Reading"
            )
        ).scalar_one()
        assert activity.goal == pytest.approx(2.5)
        assert activity.activity_type == "negative"
        assert activity.active is False
        assert activity.frequency_per_day == 2
        assert activity.frequency_per_week == 3
        assert activity.deactivated_at == "2024-05-10"


@pytest.mark.usefixtures("client")
def test_import_csv_updates_deactivated_at(tmp_path):
    with app.app_context():
        user = User(username="import_deactivated_at", password_hash="x")
        db.session.add(user)
        db.session.commit()
        user_id = user.id
        activity = Activity(
            name="Stretch",
            category="Wellness",
            activity_type="positive",
            goal=1.0,
            description="Morning stretch",
            active=False,
            frequency_per_day=1,
            frequency_per_week=7,
            deactivated_at="2024-01-01",
            user_id=user_id,
        )
        db.session.add(activity)
        db.session.commit()

    csv_content = "\n".join(
        [
            "dataset,entry_id,date,activity,entry_description,value,note,activity_category,activity_goal,activity_type",
            "entries,,2024-05-01,Stretch,Entry,0,,Wellness,1,positive",
            "",
            "dataset,activity_id,name,category,activity_type,goal,activity_description,active,frequency_per_day,frequency_per_week,deactivated_at",
            "activities,,Stretch,Wellness,positive,1.0,Morning stretch,false,1,7,2024-06-15",
        ]
    )
    csv_path = tmp_path / "export_update_deactivated_at.csv"
    csv_path.write_text(csv_content, encoding="utf-8")

    summary = import_csv(str(csv_path), user_id=user_id)
    assert summary["created"] == 1

    with app.app_context():
        updated = db.session.execute(
            select(Activity).where(Activity.user_id == user_id, Activity.name == "Stretch")
        ).scalar_one()
        assert updated.deactivated_at == "2024-06-15"
