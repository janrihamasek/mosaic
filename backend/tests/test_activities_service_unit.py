import pytest
from app import app
from repositories import activities_repo
from security import ValidationError
from services import activities_service


def _base_payload():
    return {
        "name": "Run",
        "category": "Health",
        "activity_type": "positive",
        "goal": 1,
        "description": "desc",
        "frequency_per_day": 1,
        "frequency_per_week": 7,
    }


def test_add_activity_conflict(monkeypatch):
    def fake_insert(user_id, payload, overwrite_existing=False):
        raise activities_repo.ConflictError("exists")

    monkeypatch.setattr(activities_repo, "insert_activity", fake_insert)

    with app.app_context(), pytest.raises(ValidationError) as excinfo:
        activities_service.add_activity(
            user_id=1,
            payload=_base_payload(),
            overwrite_existing=False,
            idempotency_key=None,
        )
    assert excinfo.value.status == 409


def test_delete_activity_not_found(monkeypatch):
    def fake_delete(activity_id, user_id, is_admin):
        raise activities_repo.NotFoundError("not_found")

    monkeypatch.setattr(activities_repo, "delete_activity", fake_delete)

    with app.app_context(), pytest.raises(ValidationError) as excinfo:
        activities_service.delete_activity(
            1, user_id=1, is_admin=False, invalidate_cache_cb=None
        )
    assert excinfo.value.status == 404
