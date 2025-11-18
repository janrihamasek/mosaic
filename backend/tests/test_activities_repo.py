from datetime import datetime

import pytest
from app import app
from extensions import db
from models import Activity, Entry, User
from repositories import activities_repo
from sqlalchemy import select


def _create_user(username: str = "activity_user") -> User:
    user = User(username=username, password_hash="hash", created_at=datetime.utcnow())
    db.session.add(user)
    db.session.commit()
    return user


@pytest.mark.usefixtures("client")
def test_insert_activity_and_overwrite():
    with app.app_context():
        user = _create_user("insert_user")
        payload = {
            "name": "Reading",
            "category": "Leisure",
            "activity_type": "positive",
            "goal": 1.0,
            "description": "Books",
            "frequency_per_day": 1,
            "frequency_per_week": 7,
        }
        response, status = activities_repo.insert_activity(user.id, payload)
        assert status == 201
        assert response["message"]

        row = db.session.execute(
            select(Activity).where(Activity.name == "Reading", Activity.user_id == user.id)
        ).scalar_one()
        assert row.category == "Leisure"

        with pytest.raises(activities_repo.ConflictError):
            activities_repo.insert_activity(user.id, payload, overwrite_existing=False)

        payload["category"] = "Updated"
        response, status = activities_repo.insert_activity(
            user.id, payload, overwrite_existing=True
        )
        assert status == 200
        updated = db.session.execute(
            select(Activity.category).where(Activity.name == "Reading")
        ).scalar_one()
        assert updated == "Updated"


@pytest.mark.usefixtures("client")
def test_update_activity_propagates_entries():
    with app.app_context():
        user = _create_user("update_user")
        activity = Activity(
            name="Exercise",
            category="Health",
            activity_type="positive",
            goal=2.0,
            description="Gym",
            active=True,
            frequency_per_day=1,
            frequency_per_week=7,
            user_id=user.id,
        )
        entry = Entry(
            date="2024-01-01",
            activity="Exercise",
            description="Gym",
            value=1.0,
            note="note",
            activity_category="Health",
            activity_goal=2.0,
            activity_type="positive",
            user_id=user.id,
        )
        db.session.add_all([activity, entry])
        db.session.commit()

        response, status = activities_repo.update_activity(
            activity.id,
            user.id,
            False,
            {"description": "Updated", "category": "Fitness", "goal": 5.0},
        )
        assert status == 200
        assert response["message"]

        updated_entry = db.session.execute(
            select(Entry).where(Entry.activity == "Exercise", Entry.user_id == user.id)
        ).scalar_one()
        assert updated_entry.description == "Updated"
        assert updated_entry.activity_category == "Fitness"
        assert updated_entry.activity_goal == pytest.approx(5.0)


@pytest.mark.usefixtures("client")
def test_activate_deactivate_and_delete():
    with app.app_context():
        user = _create_user("state_user")
        activity = Activity(
            name="Yoga",
            category="Health",
            activity_type="positive",
            goal=1.0,
            description="Stretch",
            active=True,
            frequency_per_day=1,
            frequency_per_week=7,
            user_id=user.id,
        )
        db.session.add(activity)
        db.session.commit()

        # cannot delete active
        with pytest.raises(activities_repo.ConflictError):
            activities_repo.delete_activity(activity.id, user.id, False)

        resp, status = activities_repo.deactivate_activity(
            activity.id, "2024-01-02", user.id, False
        )
        assert status == 200
        assert resp["message"]

        with pytest.raises(activities_repo.ConflictError):
            activities_repo.deactivate_activity(activity.id, "2024-01-03", user.id, False)

        resp, status = activities_repo.activate_activity(activity.id, user.id, False)
        assert status == 200
        assert resp["message"]

        resp, status = activities_repo.deactivate_activity(
            activity.id, "2024-01-04", user.id, False
        )
        assert status == 200

        resp, status = activities_repo.delete_activity(activity.id, user.id, False)
        assert status == 200
        assert resp["message"]

        count = db.session.execute(
            select(Activity).where(Activity.name == "Yoga")
        ).scalar_one_or_none()
        assert count is None
