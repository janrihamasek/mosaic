import pytest
from app import app
from extensions import db
from models import Activity, User
from repositories import activities_repo
from services import activities_service
from security import ValidationError
from flask import g
from controllers import activities_controller


def _create_user(username: str = "batch_user") -> User:
    user = User(username=username, password_hash="hash")  # type: ignore
    db.session.add(user)
    db.session.commit()
    return user


def _add_activity(
    user_id: int,
    name: str,
    *,
    active: bool = True,
    category: str = "Cat",
    activity_type: str = "positive",
) -> Activity:
    activity = Activity(  # type: ignore
        name=name,
        category=category,
        activity_type=activity_type,
        goal=1.0,
        description="desc",
        active=active,
        frequency_per_day=1,
        frequency_per_week=7,
        user_id=user_id,
    )
    db.session.add(activity)
    db.session.commit()
    return activity


@pytest.mark.usefixtures("client")
def test_batch_repo_processes_and_skips():
    with app.app_context():
        user = _create_user()
        active = _add_activity(user.id, "ActiveA", active=True)
        inactive = _add_activity(user.id, "InactiveA", active=False)

        summary = activities_repo.batch_update_activities(
            "deactivate", [active.id, inactive.id, 999], user.id, False
        )
        assert active.id in summary["processed"]
        assert any(item["reason"] == "already_inactive" for item in summary["skipped"])
        assert any(item["reason"] == "not_found" for item in summary["skipped"])

        fresh_active = _add_activity(user.id, "ActiveB", active=True)
        summary_delete = activities_repo.batch_update_activities(
            "delete", [inactive.id, fresh_active.id], user.id, False
        )
        assert inactive.id in summary_delete["processed"]
        assert any(
            item["reason"] == "active" and item["id"] == fresh_active.id
            for item in summary_delete["skipped"]
        )


@pytest.mark.usefixtures("client")
def test_batch_service_validation_errors():
    with app.app_context():
        with pytest.raises(ValidationError):
            activities_service.batch_update_activities(
                action="unknown", ids=[1], user_id=1, is_admin=False
            )
        with pytest.raises(ValidationError):
            activities_service.batch_update_activities(
                action="activate", ids=[], user_id=1, is_admin=False
            )


@pytest.mark.usefixtures("client")
def test_batch_controller_success(monkeypatch):
    with app.app_context():
        user = _create_user("controller_user")
        activity = _add_activity(user.id, "A1", active=True)

        # Deactivate then reactivate to exercise processed path
        activities_repo.batch_update_activities("deactivate", [activity.id], user.id, False)

        with app.test_request_context(
            "/activities/batch",
            method="POST",
            json={"action": "activate", "ids": [activity.id]},
        ):
            g.current_user = {"id": user.id, "is_admin": False}  # type: ignore
            resp, status = activities_controller.batch_update_activities()
            assert status == 200
            payload = resp.get_json()
            assert payload["processed"] == [activity.id]
