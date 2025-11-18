from datetime import datetime

import pytest
from app import app
from extensions import db
from models import Activity, Entry, User
from repositories import entries_repo
from sqlalchemy import select


def _create_user(username: str = "user_repo") -> User:
    user = User(username=username, password_hash="hash", created_at=datetime.utcnow())
    db.session.add(user)
    db.session.commit()
    return user


@pytest.mark.usefixtures("client")
def test_upsert_creates_and_updates_entry():
    with app.app_context():
        user = _create_user("repo_create")
        payload, status = entries_repo.upsert_entry_with_metadata_check(
            user.id, "2024-01-01", "Exercise", 3.0, "note"
        )
        assert status == 201
        assert payload["message"]

        row = db.session.execute(
            select(Entry).where(Entry.user_id == user.id, Entry.activity == "Exercise")
        ).scalar_one()
        assert row.value == pytest.approx(3.0)
        assert row.note == "note"

        payload, status = entries_repo.upsert_entry_with_metadata_check(
            user.id, "2024-01-01", "Exercise", 4.0, "updated"
        )
        assert status == 200
        assert payload["message"]

        updated = db.session.execute(
            select(Entry).where(Entry.user_id == user.id, Entry.activity == "Exercise")
        ).scalar_one()
        assert updated.value == pytest.approx(4.0)
        assert updated.note == "updated"


@pytest.mark.usefixtures("client")
def test_upsert_adopts_shared_entry():
    with app.app_context():
        user = _create_user("repo_adopt")
        shared_entry = Entry(
            date="2024-02-01",
            activity="Read",
            description="existing",
            value=1.0,
            note="shared",
            activity_category="Leisure",
            activity_goal=1.0,
            activity_type="positive",
            user_id=None,
        )
        db.session.add(shared_entry)
        db.session.commit()

        payload, status = entries_repo.upsert_entry_with_metadata_check(
            user.id, "2024-02-01", "Read", 2.0, "claimed"
        )
        assert status == 200
        assert payload["message"]

        adopted = db.session.execute(
            select(Entry).where(Entry.activity == "Read", Entry.date == "2024-02-01")
        ).scalar_one()
        assert adopted.user_id == user.id
        assert adopted.value == pytest.approx(2.0)
        assert adopted.note == "claimed"


@pytest.mark.usefixtures("client")
def test_create_missing_entries_for_day():
    with app.app_context():
        user = _create_user("repo_finalize")
        coding = Activity(
            name="Coding",
            category="Work",
            goal=1.0,
            description="dev",
            active=True,
            frequency_per_day=1,
            frequency_per_week=7,
            user_id=user.id,
        )
        workout = Activity(
            name="Workout",
            category="Health",
            goal=2.0,
            description="gym",
            active=True,
            frequency_per_day=1,
            frequency_per_week=7,
            user_id=user.id,
        )
        db.session.add_all([coding, workout])
        db.session.flush()

        existing = Entry(
            date="2024-03-01",
            activity="Coding",
            description="dev",
            value=1,
            note="done",
            activity_category="Work",
            activity_goal=1.0,
            activity_type="positive",
            user_id=user.id,
        )
        db.session.add(existing)
        db.session.commit()

        created = entries_repo.create_missing_entries_for_day(
            user.id, "2024-03-01", False
        )
        assert created == 1

        rows = db.session.execute(
            select(Entry).where(Entry.date == "2024-03-01")
        ).scalars().all()
        assert len(rows) == 2
        activities = {row.activity for row in rows}
        assert activities == {"Coding", "Workout"}
