from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List, Optional

from sqlalchemy.orm import DynamicMapped, Mapped, mapped_column, relationship

from extensions import db


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Activity(db.Model):
    __tablename__ = "activities"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(db.String(120), nullable=False, unique=True)
    category: Mapped[str] = mapped_column(db.String(120), nullable=False, default="")
    activity_type: Mapped[str] = mapped_column(
        db.String(16),
        nullable=False,
        default="positive",
        server_default="positive",
    )
    goal: Mapped[float] = mapped_column(db.Float, nullable=False, default=0.0)
    description: Mapped[Optional[str]] = mapped_column(db.Text, nullable=True)
    active: Mapped[bool] = mapped_column(db.Boolean, nullable=False, default=True)
    frequency_per_day: Mapped[int] = mapped_column(db.Integer, nullable=False, default=1)
    frequency_per_week: Mapped[int] = mapped_column(db.Integer, nullable=False, default=1)
    deactivated_at: Mapped[Optional[str]] = mapped_column(db.String(32), nullable=True)
    user_id: Mapped[Optional[int]] = mapped_column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    user: Mapped[Optional["User"]] = relationship(back_populates="activities")

    def __repr__(self) -> str:  # pragma: no cover - convenience
        status = "active" if self.active else f"inactive since {self.deactivated_at}"
        return f"<Activity {self.name} ({status})>"


class Entry(db.Model):
    __tablename__ = "entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    date: Mapped[str] = mapped_column(db.String(10), nullable=False)
    activity: Mapped[str] = mapped_column(db.String(120), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(db.Text, nullable=True)
    value: Mapped[Optional[float]] = mapped_column(db.Float, nullable=True, default=0.0)
    note: Mapped[Optional[str]] = mapped_column(db.Text, nullable=True)
    activity_category: Mapped[str] = mapped_column(db.String(120), nullable=False, default="")
    activity_goal: Mapped[float] = mapped_column(db.Float, nullable=False, default=0.0)
    user_id: Mapped[Optional[int]] = mapped_column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    user: Mapped[Optional["User"]] = relationship(back_populates="entries")

    def __repr__(self) -> str:  # pragma: no cover - convenience
        return f"<Entry {self.date} {self.activity}>"


class User(db.Model):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(db.String(80), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(db.String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(db.DateTime, nullable=False, default=datetime.utcnow)
    is_admin: Mapped[bool] = mapped_column(db.Boolean, nullable=False, default=False)
    display_name: Mapped[str] = mapped_column(db.String(120), nullable=False, default="")

    activities: Mapped[List["Activity"]] = relationship(
        back_populates="user",
        passive_deletes=True,
    )
    entries: Mapped[List["Entry"]] = relationship(
        back_populates="user",
        passive_deletes=True,
    )
    activity_logs: DynamicMapped["ActivityLog"] = relationship(
        "ActivityLog",
        back_populates="user",
        lazy="dynamic",
    )
    wearable_sources: Mapped[List["WearableSource"]] = relationship(
        "WearableSource",
        back_populates="user",
        passive_deletes=True,
    )
    wearable_raw_records: Mapped[List["WearableRaw"]] = relationship(
        "WearableRaw",
        back_populates="user",
        passive_deletes=True,
    )
    wearable_steps: Mapped[List["WearableCanonicalSteps"]] = relationship(
        "WearableCanonicalSteps",
        back_populates="user",
        passive_deletes=True,
    )
    wearable_hr: Mapped[List["WearableCanonicalHR"]] = relationship(
        "WearableCanonicalHR",
        back_populates="user",
        passive_deletes=True,
    )
    wearable_sleep_sessions: Mapped[List["WearableCanonicalSleepSession"]] = relationship(
        "WearableCanonicalSleepSession",
        back_populates="user",
        passive_deletes=True,
    )
    wearable_sleep_stages: Mapped[List["WearableCanonicalSleepStage"]] = relationship(
        "WearableCanonicalSleepStage",
        back_populates="user",
        passive_deletes=True,
    )
    wearable_daily_agg: Mapped[List["WearableDailyAgg"]] = relationship(
        "WearableDailyAgg",
        back_populates="user",
        passive_deletes=True,
    )

    def __repr__(self) -> str:  # pragma: no cover - convenience
        return f"<User {self.username}>"


class BackupSettings(db.Model):
    __tablename__ = "backup_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    enabled: Mapped[bool] = mapped_column(db.Boolean, nullable=False, default=False)
    interval_minutes: Mapped[int] = mapped_column(db.Integer, nullable=False, default=60)
    last_run: Mapped[Optional[datetime]] = mapped_column(db.DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:  # pragma: no cover - convenience
        status = "enabled" if self.enabled else "disabled"
        return f"<BackupSettings {status} interval={self.interval_minutes} last_run={self.last_run}>"


class ActivityLog(db.Model):
    __tablename__ = "activity_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(
        db.DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
        index=True,
    )
    user_id: Mapped[Optional[int]] = mapped_column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(db.String(64), nullable=False, index=True)
    message: Mapped[str] = mapped_column(db.Text, nullable=False)
    context: Mapped[Optional[Dict[str, object]]] = mapped_column(db.JSON, nullable=True)
    level: Mapped[str] = mapped_column(db.String(20), nullable=False, default="info", index=True)

    user: Mapped[Optional["User"]] = relationship(back_populates="activity_logs")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "user_id": self.user_id,
            "event_type": self.event_type,
            "message": self.message,
            "context": self.context or {},
            "level": self.level,
        }

    def __repr__(self) -> str:  # pragma: no cover - convenience
        return f"<ActivityLog {self.event_type} ({self.level})>"


class WearableSource(db.Model):
    __tablename__ = "wearable_sources"
    __table_args__ = (
        db.UniqueConstraint("dedupe_key", name="uq_wearable_sources_dedupe_key"),
        db.UniqueConstraint("user_id", "provider", "external_id", name="uq_wearable_sources_user_provider_external"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    provider: Mapped[str] = mapped_column(db.String(64), nullable=False)
    external_id: Mapped[str] = mapped_column(db.String(128), nullable=False)
    display_name: Mapped[Optional[str]] = mapped_column(db.String(128), nullable=True)
    sync_metadata: Mapped[Optional[Dict[str, object]]] = mapped_column(db.JSON, nullable=True)
    last_synced_at: Mapped[Optional[datetime]] = mapped_column(db.DateTime(timezone=True), nullable=True)
    dedupe_key: Mapped[str] = mapped_column(db.String(255), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(db.DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        db.DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
        onupdate=_utcnow,
    )

    user: Mapped["User"] = relationship(back_populates="wearable_sources")
    raw_records: Mapped[List["WearableRaw"]] = relationship(
        "WearableRaw",
        back_populates="source",
        passive_deletes=True,
    )
    canonical_steps: Mapped[List["WearableCanonicalSteps"]] = relationship(
        "WearableCanonicalSteps",
        back_populates="source",
        passive_deletes=True,
    )
    canonical_hr: Mapped[List["WearableCanonicalHR"]] = relationship(
        "WearableCanonicalHR",
        back_populates="source",
        passive_deletes=True,
    )
    sleep_sessions: Mapped[List["WearableCanonicalSleepSession"]] = relationship(
        "WearableCanonicalSleepSession",
        back_populates="source",
        passive_deletes=True,
    )
    daily_aggregates: Mapped[List["WearableDailyAgg"]] = relationship(
        "WearableDailyAgg",
        back_populates="source",
        passive_deletes=True,
    )


class WearableRaw(db.Model):
    __tablename__ = "wearable_raw"
    __table_args__ = (
        db.UniqueConstraint("dedupe_key", name="uq_wearable_raw_dedupe_key"),
        db.Index("ix_wearable_raw_user_collected_at", "user_id", "collected_at_utc"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_id: Mapped[Optional[int]] = mapped_column(
        db.Integer,
        db.ForeignKey("wearable_sources.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    collected_at_utc: Mapped[datetime] = mapped_column(db.DateTime(timezone=True), nullable=False)
    received_at_utc: Mapped[datetime] = mapped_column(
        db.DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
    )
    payload: Mapped[Dict[str, object]] = mapped_column(db.JSON, nullable=False)
    dedupe_key: Mapped[str] = mapped_column(db.String(255), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(db.DateTime(timezone=True), nullable=False, default=_utcnow)

    user: Mapped["User"] = relationship(back_populates="wearable_raw_records")
    source: Mapped[Optional["WearableSource"]] = relationship(back_populates="raw_records")
    canonical_steps: Mapped[List["WearableCanonicalSteps"]] = relationship(
        "WearableCanonicalSteps",
        back_populates="raw",
        passive_deletes=True,
    )
    canonical_hr: Mapped[List["WearableCanonicalHR"]] = relationship(
        "WearableCanonicalHR",
        back_populates="raw",
        passive_deletes=True,
    )
    sleep_sessions: Mapped[List["WearableCanonicalSleepSession"]] = relationship(
        "WearableCanonicalSleepSession",
        back_populates="raw",
        passive_deletes=True,
    )


class WearableCanonicalSteps(db.Model):
    __tablename__ = "wearable_canonical_steps"
    __table_args__ = (
        db.UniqueConstraint("dedupe_key", name="uq_wearable_canonical_steps_dedupe_key"),
        db.Index("ix_wearable_canonical_steps_user_start", "user_id", "start_time_utc"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_id: Mapped[Optional[int]] = mapped_column(
        db.Integer,
        db.ForeignKey("wearable_sources.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    raw_id: Mapped[Optional[int]] = mapped_column(
        db.Integer,
        db.ForeignKey("wearable_raw.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    start_time_utc: Mapped[datetime] = mapped_column(db.DateTime(timezone=True), nullable=False)
    end_time_utc: Mapped[datetime] = mapped_column(db.DateTime(timezone=True), nullable=False)
    steps: Mapped[int] = mapped_column(db.Integer, nullable=False, default=0)
    distance_meters: Mapped[Optional[float]] = mapped_column(db.Float, nullable=True)
    active_minutes: Mapped[Optional[int]] = mapped_column(db.Integer, nullable=True)
    dedupe_key: Mapped[str] = mapped_column(db.String(255), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(db.DateTime(timezone=True), nullable=False, default=_utcnow)

    user: Mapped["User"] = relationship(back_populates="wearable_steps")
    source: Mapped[Optional["WearableSource"]] = relationship(back_populates="canonical_steps")
    raw: Mapped[Optional["WearableRaw"]] = relationship(back_populates="canonical_steps")


class WearableCanonicalHR(db.Model):
    __tablename__ = "wearable_canonical_hr"
    __table_args__ = (
        db.UniqueConstraint("dedupe_key", name="uq_wearable_canonical_hr_dedupe_key"),
        db.Index("ix_wearable_canonical_hr_user_timestamp", "user_id", "timestamp_utc"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_id: Mapped[Optional[int]] = mapped_column(
        db.Integer,
        db.ForeignKey("wearable_sources.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    raw_id: Mapped[Optional[int]] = mapped_column(
        db.Integer,
        db.ForeignKey("wearable_raw.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    timestamp_utc: Mapped[datetime] = mapped_column(db.DateTime(timezone=True), nullable=False)
    bpm: Mapped[int] = mapped_column(db.Integer, nullable=False)
    confidence: Mapped[Optional[str]] = mapped_column(db.String(32), nullable=True)
    variability_ms: Mapped[Optional[float]] = mapped_column(db.Float, nullable=True)
    dedupe_key: Mapped[str] = mapped_column(db.String(255), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(db.DateTime(timezone=True), nullable=False, default=_utcnow)

    user: Mapped["User"] = relationship(back_populates="wearable_hr")
    source: Mapped[Optional["WearableSource"]] = relationship(back_populates="canonical_hr")
    raw: Mapped[Optional["WearableRaw"]] = relationship(back_populates="canonical_hr")


class WearableCanonicalSleepSession(db.Model):
    __tablename__ = "wearable_canonical_sleep_sessions"
    __table_args__ = (
        db.UniqueConstraint("dedupe_key", name="uq_wearable_canonical_sleep_sessions_dedupe_key"),
        db.Index("ix_wearable_sleep_sessions_user_start", "user_id", "start_time_utc"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_id: Mapped[Optional[int]] = mapped_column(
        db.Integer,
        db.ForeignKey("wearable_sources.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    raw_id: Mapped[Optional[int]] = mapped_column(
        db.Integer,
        db.ForeignKey("wearable_raw.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    start_time_utc: Mapped[datetime] = mapped_column(db.DateTime(timezone=True), nullable=False)
    end_time_utc: Mapped[datetime] = mapped_column(db.DateTime(timezone=True), nullable=False)
    duration_seconds: Mapped[Optional[int]] = mapped_column(db.Integer, nullable=True)
    sleep_type: Mapped[Optional[str]] = mapped_column(db.String(32), nullable=True)
    score: Mapped[Optional[int]] = mapped_column(db.Integer, nullable=True)
    dedupe_key: Mapped[str] = mapped_column(db.String(255), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(db.DateTime(timezone=True), nullable=False, default=_utcnow)

    user: Mapped["User"] = relationship(back_populates="wearable_sleep_sessions")
    source: Mapped[Optional["WearableSource"]] = relationship(back_populates="sleep_sessions")
    raw: Mapped[Optional["WearableRaw"]] = relationship(back_populates="sleep_sessions")
    stages: Mapped[List["WearableCanonicalSleepStage"]] = relationship(
        "WearableCanonicalSleepStage",
        back_populates="session",
        passive_deletes=True,
    )


class WearableCanonicalSleepStage(db.Model):
    __tablename__ = "wearable_canonical_sleep_stages"
    __table_args__ = (
        db.UniqueConstraint("dedupe_key", name="uq_wearable_canonical_sleep_stages_dedupe_key"),
        db.Index("ix_wearable_sleep_stages_user_start", "user_id", "start_time_utc"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(
        db.Integer,
        db.ForeignKey("wearable_canonical_sleep_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[int] = mapped_column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    stage_type: Mapped[str] = mapped_column(db.String(32), nullable=False)
    start_time_utc: Mapped[datetime] = mapped_column(db.DateTime(timezone=True), nullable=False)
    end_time_utc: Mapped[datetime] = mapped_column(db.DateTime(timezone=True), nullable=False)
    duration_seconds: Mapped[Optional[int]] = mapped_column(db.Integer, nullable=True)
    dedupe_key: Mapped[str] = mapped_column(db.String(255), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(db.DateTime(timezone=True), nullable=False, default=_utcnow)

    session: Mapped["WearableCanonicalSleepSession"] = relationship(back_populates="stages")
    user: Mapped["User"] = relationship(back_populates="wearable_sleep_stages")


class WearableDailyAgg(db.Model):
    __tablename__ = "wearable_daily_agg"
    __table_args__ = (
        db.UniqueConstraint("dedupe_key", name="uq_wearable_daily_agg_dedupe_key"),
        db.Index("ix_wearable_daily_agg_user_day", "user_id", "day_start_utc"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_id: Mapped[Optional[int]] = mapped_column(
        db.Integer,
        db.ForeignKey("wearable_sources.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    day_start_utc: Mapped[datetime] = mapped_column(db.DateTime(timezone=True), nullable=False)
    steps: Mapped[Optional[int]] = mapped_column(db.Integer, nullable=True)
    distance_meters: Mapped[Optional[float]] = mapped_column(db.Float, nullable=True)
    calories: Mapped[Optional[float]] = mapped_column(db.Float, nullable=True)
    resting_heart_rate: Mapped[Optional[int]] = mapped_column(db.Integer, nullable=True)
    hrv_rmssd_ms: Mapped[Optional[float]] = mapped_column(db.Float, nullable=True)
    sleep_seconds: Mapped[Optional[int]] = mapped_column(db.Integer, nullable=True)
    payload: Mapped[Optional[Dict[str, object]]] = mapped_column(db.JSON, nullable=True)
    dedupe_key: Mapped[str] = mapped_column(db.String(255), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(db.DateTime(timezone=True), nullable=False, default=_utcnow)

    user: Mapped["User"] = relationship(back_populates="wearable_daily_agg")
    source: Mapped[Optional["WearableSource"]] = relationship(back_populates="daily_aggregates")


__all__ = [
    "Activity",
    "Entry",
    "User",
    "BackupSettings",
    "ActivityLog",
    "WearableSource",
    "WearableRaw",
    "WearableCanonicalSteps",
    "WearableCanonicalHR",
    "WearableCanonicalSleepSession",
    "WearableCanonicalSleepStage",
    "WearableDailyAgg",
]
