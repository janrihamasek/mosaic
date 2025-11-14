from datetime import date
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class WearableSleepSummary(BaseModel):
    total_min: float = Field(..., ge=0)
    efficiency: Optional[float] = None
    sessions: int = Field(..., ge=0)


class WearableHrSummary(BaseModel):
    rest: Optional[int] = None
    avg: Optional[float] = None
    min: Optional[int] = None
    max: Optional[int] = None


class WearableDayResponse(BaseModel):
    date: str
    steps: int = Field(..., ge=0)
    sleep: WearableSleepSummary
    hr: WearableHrSummary

    model_config = ConfigDict(extra="forbid")


class WearableTrendPoint(BaseModel):
    date: str
    value: Optional[float]


class WearableTrendsResponse(BaseModel):
    metric: str
    window: int
    average: Optional[float]
    values: List[WearableTrendPoint]

    model_config = ConfigDict(extra="forbid")


class WearableTrendsQuery(BaseModel):
    metric: str
    window: int

    model_config = ConfigDict(extra="forbid")

    @field_validator("metric")
    @classmethod
    def validate_metric(cls, value: str) -> str:
        normalized = (value or "").strip().lower()
        if normalized not in {"steps", "sleep", "hr"}:
            raise ValueError("metric must be one of steps, sleep, hr")
        return normalized

    @field_validator("window")
    @classmethod
    def validate_window(cls, value: int) -> int:
        if value not in {7, 30}:
            raise ValueError("window must be 7 or 30")
        return value
