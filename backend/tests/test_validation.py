import io
from datetime import datetime

import pytest
from werkzeug.datastructures import FileStorage, MultiDict

from security import (
    ValidationError,
    validate_activity_create_payload,
    validate_activity_update_payload,
    validate_csv_import_payload,
    validate_entry_payload,
    validate_finalize_day_payload,
)


def test_validate_entry_payload_success():
    payload = {
        "date": "2024-01-01",
        "activity": "  Reading  ",
        "value": "3.5",
        "note": "  Evening session ",
    }
    validated = validate_entry_payload(payload)
    assert validated == {
        "date": "2024-01-01",
        "activity": "Reading",
        "value": 3.5,
        "note": "Evening session",
    }


def test_validate_entry_payload_missing_fields():
    with pytest.raises(ValidationError) as err:
        validate_entry_payload({"activity": "Run"})
    assert err.value.message == "Missing required field(s): date"
    assert err.value.details["fields"] == ["date"]


def test_validate_activity_create_payload_invalid_frequency():
    payload = {
        "name": "Swim",
        "category": "Health",
        "frequency_per_day": 4,
        "frequency_per_week": 7,
        "description": "Cardio",
    }
    with pytest.raises(ValidationError) as err:
        validate_activity_create_payload(payload)
    assert err.value.message == "frequency_per_day must be at most 3"


def test_validate_activity_update_payload_requires_pairs():
    with pytest.raises(ValidationError) as err:
        validate_activity_update_payload({"frequency_per_day": 2})
    assert err.value.message == "Both frequency_per_day and frequency_per_week must be provided together"


def test_validate_activity_update_payload_overrides_goal_with_frequency():
    data = validate_activity_update_payload(
        {
            "frequency_per_day": 2,
            "frequency_per_week": 6,
            "goal": 99,
        }
    )
    assert data["frequency_per_day"] == 2
    assert data["frequency_per_week"] == 6
    assert data["goal"] == pytest.approx((2 * 6) / 7)


def test_validate_csv_import_payload_success():
    file = FileStorage(stream=io.BytesIO(b"date,activity"), filename="import.csv")
    wrapped = MultiDict({"file": file})
    validated = validate_csv_import_payload(wrapped)
    assert isinstance(validated, FileStorage)


def test_validate_csv_import_payload_missing():
    with pytest.raises(ValidationError) as err:
        validate_csv_import_payload(MultiDict())
    assert err.value.message == "Missing CSV file"


def test_validate_finalize_day_payload_defaults_today(monkeypatch):
    today = "2024-08-15"

    class FixedDateTime(datetime):
        @classmethod
        def now(cls):
            return datetime.fromisoformat(f"{today}T12:00:00")

    monkeypatch.setattr("security.datetime", FixedDateTime)
    payload = validate_finalize_day_payload({})
    assert payload["date"] == today


def test_validate_finalize_day_payload_invalid_date():
    with pytest.raises(ValidationError) as err:
        validate_finalize_day_payload({"date": "2024-99-01"})
    assert err.value.message == "Date must be in YYYY-MM-DD format"
