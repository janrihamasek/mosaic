from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from werkzeug.datastructures import FileStorage


class EntryPayload(BaseModel):
    date: str = Field(...)
    activity: str = Field(...)
    value: float = Field(default=0)
    note: str = Field(default="")

    model_config = ConfigDict(extra="forbid")

    @field_validator("date")
    @classmethod
    def validate_date(cls, value: str) -> str:
        if not isinstance(value, str):
            raise ValueError("Date must be in YYYY-MM-DD format")
        try:
            datetime.strptime(value, "%Y-%m-%d")
        except ValueError:
            raise ValueError("Date must be in YYYY-MM-DD format")
        return value

    @field_validator("activity")
    @classmethod
    def validate_activity(cls, value: str) -> str:
        value = (value or "").strip()
        if not value:
            raise ValueError("Activity must not be empty")
        return value

    @field_validator("note")
    @classmethod
    def validate_note(cls, value: str) -> str:
        value = (value or "").strip()
        if len(value) > 100:
            raise ValueError("note must be at most 100 characters")
        return value

    @field_validator("value", mode="before")
    @classmethod
    def ensure_number(cls, value):
        if value is None:
            raise ValueError("value must be a number")
        try:
            return float(value)
        except (TypeError, ValueError):
            raise ValueError("value must be a number")


class ActivityCreatePayload(BaseModel):
    name: str
    category: str
    frequency_per_day: int
    frequency_per_week: int
    description: str = ""

    model_config = ConfigDict(extra="forbid")

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        value = (value or "").strip()
        if not value:
            raise ValueError("Activity name must not be empty")
        if len(value) > 80:
            raise ValueError("name must be at most 80 characters")
        return value

    @field_validator("category")
    @classmethod
    def validate_category(cls, value: str) -> str:
        value = (value or "").strip()
        if not value:
            raise ValueError("Category must not be empty")
        if len(value) > 80:
            raise ValueError("category must be at most 80 characters")
        return value

    @field_validator("description")
    @classmethod
    def validate_description(cls, value: str) -> str:
        value = (value or "").strip()
        if len(value) > 180:
            raise ValueError("description must be at most 180 characters")
        return value

    @field_validator("frequency_per_day", mode="before")
    @classmethod
    def validate_frequency_per_day(cls, value):
        return cls._ensure_frequency(value, "frequency_per_day", minimum=1, maximum=3)

    @field_validator("frequency_per_week", mode="before")
    @classmethod
    def validate_frequency_per_week(cls, value):
        return cls._ensure_frequency(value, "frequency_per_week", minimum=1, maximum=7)

    @staticmethod
    def _ensure_frequency(value, field: str, *, minimum: int, maximum: int) -> int:
        try:
            number = int(value)
        except (TypeError, ValueError):
            raise ValueError(f"{field} must be an integer")
        if number < minimum:
            raise ValueError(f"{field} must be at least {minimum}")
        if number > maximum:
            raise ValueError(f"{field} must be at most {maximum}")
        return number

    @property
    def computed_goal(self) -> float:
        return (self.frequency_per_day * self.frequency_per_week) / 7


class ActivityUpdatePayload(BaseModel):
    category: Optional[str] = None
    goal: Optional[float] = None
    description: Optional[str] = None
    frequency_per_day: Optional[int] = None
    frequency_per_week: Optional[int] = None

    model_config = ConfigDict(extra="forbid")

    @field_validator("category")
    @classmethod
    def validate_category(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("Category must not be empty")
        if len(value) > 80:
            raise ValueError("category must be at most 80 characters")
        return value

    @field_validator("description")
    @classmethod
    def validate_description(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        value = value.strip()
        if len(value) > 180:
            raise ValueError("description must be at most 180 characters")
        return value

    @field_validator("goal", mode="before")
    @classmethod
    def validate_goal(cls, value: Optional[float]) -> Optional[float]:
        if value is None:
            return None
        try:
            number = float(value)
        except (TypeError, ValueError):
            raise ValueError("goal must be a number")
        if number < 0:
            raise ValueError("goal must be non-negative")
        return number

    @field_validator("frequency_per_day", mode="before")
    @classmethod
    def validate_frequency_per_day(cls, value):
        return cls._ensure_frequency(value, "frequency_per_day", minimum=1, maximum=3)

    @field_validator("frequency_per_week", mode="before")
    @classmethod
    def validate_frequency_per_week(cls, value):
        return cls._ensure_frequency(value, "frequency_per_week", minimum=1, maximum=7)

    @staticmethod
    def _ensure_frequency(value, field: str, *, minimum: int, maximum: int) -> Optional[int]:
        if value is None:
            return None
        try:
            number = int(value)
        except (TypeError, ValueError):
            raise ValueError(f"{field} must be an integer")
        if number < minimum:
            raise ValueError(f"{field} must be at least {minimum}")
        if number > maximum:
            raise ValueError(f"{field} must be at most {maximum}")
        return number

    @model_validator(mode="after")
    def validate_combinations(self):
        data = self.model_dump(exclude_none=True)
        if not data:
            raise ValueError("No updatable fields provided")
        freq_day = data.get("frequency_per_day")
        freq_week = data.get("frequency_per_week")
        if (freq_day is None) ^ (freq_week is None):
            raise ValueError("Both frequency_per_day and frequency_per_week must be provided together")
        return self

    def to_update_dict(self) -> dict:
        data = self.model_dump(exclude_none=True, exclude_unset=True)
        freq_day = data.get("frequency_per_day")
        freq_week = data.get("frequency_per_week")
        if freq_day is not None and freq_week is not None:
            data["goal"] = (freq_day * freq_week) / 7
        return data


class CSVImportPayload(BaseModel):
    file: FileStorage

    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    @field_validator("file")
    @classmethod
    def validate_file(cls, value: FileStorage) -> FileStorage:
        if not isinstance(value, FileStorage):
            raise ValueError("Missing CSV file")
        if not getattr(value, "filename", None):
            raise ValueError("Missing CSV file")
        return value


class FinalizeDayPayload(BaseModel):
    date: Optional[str] = None

    model_config = ConfigDict(extra="forbid")

    @field_validator("date")
    @classmethod
    def validate_date(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError("Date must be in YYYY-MM-DD format")
        try:
            datetime.strptime(value, "%Y-%m-%d")
        except ValueError:
            raise ValueError("Date must be in YYYY-MM-DD format")
        return value


class RegisterPayload(BaseModel):
    username: str
    password: str

    model_config = ConfigDict(extra="forbid")

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        username = (value or "").strip()
        if len(username) < 3:
            raise ValueError("username must be at least 3 characters")
        if len(username) > 80:
            raise ValueError("username must be at most 80 characters")
        if " " in username:
            raise ValueError("username must not contain spaces")
        return username

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if not isinstance(value, str) or len(value) < 8:
            raise ValueError("password must be at least 8 characters")
        return value


class LoginPayload(BaseModel):
    username: str
    password: str

    model_config = ConfigDict(extra="forbid")

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        username = (value or "").strip()
        if not username:
            raise ValueError("username must not be empty")
        return username

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if not isinstance(value, str) or not value:
            raise ValueError("password must not be empty")
        return value
