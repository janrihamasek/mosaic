from datetime import datetime
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator, model_validator
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


ALLOWED_ACTIVITY_TYPES = {"positive", "negative"}


class ActivityCreatePayload(BaseModel):
    name: str
    category: str
    frequency_per_day: int
    frequency_per_week: int
    description: str = ""
    goal: Optional[float] = None
    activity_type: str = Field(default="positive")

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

    @field_validator("activity_type")
    @classmethod
    def validate_activity_type(cls, value: str) -> str:
        value = (value or "").strip().lower()
        if value not in ALLOWED_ACTIVITY_TYPES:
            allowed = ", ".join(sorted(ALLOWED_ACTIVITY_TYPES))
            raise ValueError(f"activity_type must be one of: {allowed}")
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
    activity_type: Optional[str] = None

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

    @field_validator("activity_type")
    @classmethod
    def validate_activity_type(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        normalized = value.strip().lower()
        if normalized not in ALLOWED_ACTIVITY_TYPES:
            allowed = ", ".join(sorted(ALLOWED_ACTIVITY_TYPES))
            raise ValueError(f"activity_type must be one of: {allowed}")
        return normalized

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


class CSVImportRow(BaseModel):
    date: str
    activity: str
    value: float = 0.0
    note: str = ""
    description: str = ""
    category: str = ""
    goal: float = 0.0
    frequency_per_day: Optional[int] = None
    frequency_per_week: Optional[int] = None

    model_config = ConfigDict(extra="ignore")

    @field_validator("date", mode="before")
    @classmethod
    def normalize_date(cls, value):
        if value is None:
            raise ValueError("date is required")
        date_str = str(value).strip()
        if not date_str:
            raise ValueError("date is required")
        try:
            if "/" in date_str:
                parsed = datetime.strptime(date_str, "%d/%m/%Y")
            else:
                parsed = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            raise ValueError("date must be in YYYY-MM-DD format")
        return parsed.strftime("%Y-%m-%d")

    @field_validator("activity", mode="before")
    @classmethod
    def normalize_activity(cls, value):
        if value is None:
            raise ValueError("activity is required")
        activity = str(value).strip()
        if not activity:
            raise ValueError("activity is required")
        if len(activity) > 120:
            raise ValueError("activity must be at most 120 characters")
        return activity

    @field_validator("value", mode="before")
    @classmethod
    def parse_value(cls, value):
        if value in (None, ""):
            return 0.0
        try:
            return float(value)
        except (TypeError, ValueError):
            raise ValueError("value must be a number")

    @field_validator("goal", mode="before")
    @classmethod
    def parse_goal(cls, value):
        if value in (None, ""):
            return 0.0
        try:
            number = float(value)
        except (TypeError, ValueError):
            raise ValueError("goal must be a number")
        if number < 0:
            raise ValueError("goal must be non-negative")
        return number

    @field_validator("note", "description", "category", mode="before")
    @classmethod
    def normalize_text(cls, value):
        if value is None:
            return ""
        return str(value).strip()

    @field_validator("note")
    @classmethod
    def ensure_note_length(cls, value: str) -> str:
        if len(value) > 100:
            raise ValueError("note must be at most 100 characters")
        return value

    @field_validator("frequency_per_day", "frequency_per_week", mode="before")
    @classmethod
    def parse_frequency(cls, value, info: ValidationInfo):
        if value in (None, ""):
            return None
        try:
            number = int(value)
        except (TypeError, ValueError):
            raise ValueError(f"{info.field_name} must be an integer")
        if number < 0:
            raise ValueError(f"{info.field_name} must be non-negative")
        return number

    @model_validator(mode="after")
    def set_frequency_defaults(self):
        if self.frequency_per_day is None:
            self.frequency_per_day = 1
        if self.frequency_per_week is None:
            self.frequency_per_week = 1
        return self


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
    display_name: Optional[str] = None

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

    @field_validator("display_name")
    @classmethod
    def validate_display_name(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        name = value.strip()
        if not name:
            return None
        if len(name) > 120:
            raise ValueError("display_name must be at most 120 characters")
        return name


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


class UserUpdatePayload(BaseModel):
    display_name: Optional[str] = None
    password: Optional[str] = None

    model_config = ConfigDict(extra="forbid")

    @field_validator("display_name")
    @classmethod
    def validate_display_name(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        name = value.strip()
        if not name:
            raise ValueError("display_name must not be empty")
        if len(name) > 120:
            raise ValueError("display_name must be at most 120 characters")
        return name

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        if not isinstance(value, str) or len(value) < 8:
            raise ValueError("password must be at least 8 characters")
        return value

    @model_validator(mode="after")
    def ensure_any_field(self):
        data = self.model_dump(exclude_none=True)
        if not data:
            raise ValueError("At least one field must be provided")
        return self


class WearableRecordPayload(BaseModel):
    type: str
    start: datetime
    end: Optional[datetime] = None
    fields: Dict[str, Any]
    dedupe_key: str

    model_config = ConfigDict(extra="forbid")

    @field_validator("type")
    @classmethod
    def validate_type(cls, value: str) -> str:
        text = (value or "").strip()
        if not text:
            raise ValueError("type must not be empty")
        if len(text) > 64:
            raise ValueError("type must be at most 64 characters")
        return text

    @field_validator("fields")
    @classmethod
    def validate_fields(cls, value: Dict[str, Any]) -> Dict[str, Any]:
        if value is None:
            raise ValueError("fields must be an object")
        if not isinstance(value, dict):
            raise ValueError("fields must be an object")
        return value

    @field_validator("dedupe_key")
    @classmethod
    def validate_dedupe_key(cls, value: str) -> str:
        key = (value or "").strip()
        if not key:
            raise ValueError("dedupe_key must not be empty")
        if len(key) > 255:
            raise ValueError("dedupe_key must be at most 255 characters")
        return key


class WearableBatchPayload(BaseModel):
    source_app: str
    device_id: str
    tz: str
    records: List[WearableRecordPayload]

    model_config = ConfigDict(extra="forbid")

    @field_validator("source_app", "device_id")
    @classmethod
    def validate_text(cls, value: str, info: ValidationInfo) -> str:
        text = (value or "").strip()
        if not text:
            raise ValueError(f"{info.field_name} must not be empty")
        if len(text) > 128:
            raise ValueError(f"{info.field_name} must be at most 128 characters")
        return text

    @field_validator("tz")
    @classmethod
    def validate_timezone(cls, value: str) -> str:
        tz_value = (value or "").strip()
        if not tz_value:
            raise ValueError("tz must not be empty")
        try:
            ZoneInfo(tz_value)
        except ZoneInfoNotFoundError:
            raise ValueError("Invalid timezone identifier")
        return tz_value

    @field_validator("records")
    @classmethod
    def validate_records(cls, value: List[WearableRecordPayload]) -> List[WearableRecordPayload]:
        if not value:
            raise ValueError("records must contain at least one item")
        return value
