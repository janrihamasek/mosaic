from datetime import datetime, timezone

from extensions import db


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Activity(db.Model):
    __tablename__ = "activities"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, unique=True)
    category = db.Column(db.String(120), nullable=False, default="")
    goal = db.Column(db.Float, nullable=False, default=0.0)
    description = db.Column(db.Text, nullable=True)
    active = db.Column(db.Boolean, nullable=False, default=True)
    frequency_per_day = db.Column(db.Integer, nullable=False, default=1)
    frequency_per_week = db.Column(db.Integer, nullable=False, default=1)
    deactivated_at = db.Column(db.String(32), nullable=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    user = db.relationship("User", back_populates="activities")

    def __repr__(self) -> str:  # pragma: no cover - convenience
        status = "active" if self.active else f"inactive since {self.deactivated_at}"
        return f"<Activity {self.name} ({status})>"


class Entry(db.Model):
    __tablename__ = "entries"

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String(10), nullable=False)
    activity = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=True)
    value = db.Column(db.Float, nullable=True, default=0.0)
    note = db.Column(db.Text, nullable=True)
    activity_category = db.Column(db.String(120), nullable=False, default="")
    activity_goal = db.Column(db.Float, nullable=False, default=0.0)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    user = db.relationship("User", back_populates="entries")

    def __repr__(self) -> str:  # pragma: no cover - convenience
        return f"<Entry {self.date} {self.activity}>"


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    is_admin = db.Column(db.Boolean, nullable=False, default=False)
    display_name = db.Column(db.String(120), nullable=False, default="")

    activities = db.relationship("Activity", back_populates="user", passive_deletes=True)
    entries = db.relationship("Entry", back_populates="user", passive_deletes=True)

    def __repr__(self) -> str:  # pragma: no cover - convenience
        return f"<User {self.username}>"


class BackupSettings(db.Model):
    __tablename__ = "backup_settings"

    id = db.Column(db.Integer, primary_key=True)
    enabled = db.Column(db.Boolean, nullable=False, default=False)
    interval_minutes = db.Column(db.Integer, nullable=False, default=60)
    last_run = db.Column(db.DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:  # pragma: no cover - convenience
        status = "enabled" if self.enabled else "disabled"
        return f"<BackupSettings {status} interval={self.interval_minutes} last_run={self.last_run}>"


class ActivityLog(db.Model):
    __tablename__ = "activity_logs"

    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow, index=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    event_type = db.Column(db.String(64), nullable=False, index=True)
    message = db.Column(db.Text, nullable=False)
    context = db.Column(db.JSON, nullable=True)
    level = db.Column(db.String(20), nullable=False, default="info", index=True)

    user = db.relationship("User", backref=db.backref("activity_logs", lazy="dynamic"))

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

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    provider = db.Column(db.String(64), nullable=False)
    external_id = db.Column(db.String(128), nullable=False)
    display_name = db.Column(db.String(128), nullable=True)
    sync_metadata = db.Column(db.JSON, nullable=True)
    last_synced_at = db.Column(db.DateTime(timezone=True), nullable=True)
    dedupe_key = db.Column(db.String(255), nullable=False, unique=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
        onupdate=_utcnow,
    )

    user = db.relationship("User", backref=db.backref("wearable_sources", passive_deletes=True))


class WearableRaw(db.Model):
    __tablename__ = "wearable_raw"
    __table_args__ = (
        db.UniqueConstraint("dedupe_key", name="uq_wearable_raw_dedupe_key"),
        db.Index("ix_wearable_raw_user_collected_at", "user_id", "collected_at_utc"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_id = db.Column(
        db.Integer,
        db.ForeignKey("wearable_sources.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    collected_at_utc = db.Column(db.DateTime(timezone=True), nullable=False)
    received_at_utc = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow)
    payload = db.Column(db.JSON, nullable=False)
    dedupe_key = db.Column(db.String(255), nullable=False, unique=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow)

    user = db.relationship("User", backref=db.backref("wearable_raw_records", passive_deletes=True))
    source = db.relationship("WearableSource", backref=db.backref("raw_records", passive_deletes=True))


class WearableCanonicalSteps(db.Model):
    __tablename__ = "wearable_canonical_steps"
    __table_args__ = (
        db.UniqueConstraint("dedupe_key", name="uq_wearable_canonical_steps_dedupe_key"),
        db.Index("ix_wearable_canonical_steps_user_start", "user_id", "start_time_utc"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_id = db.Column(
        db.Integer,
        db.ForeignKey("wearable_sources.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    raw_id = db.Column(
        db.Integer,
        db.ForeignKey("wearable_raw.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    start_time_utc = db.Column(db.DateTime(timezone=True), nullable=False)
    end_time_utc = db.Column(db.DateTime(timezone=True), nullable=False)
    steps = db.Column(db.Integer, nullable=False, default=0)
    distance_meters = db.Column(db.Float, nullable=True)
    active_minutes = db.Column(db.Integer, nullable=True)
    dedupe_key = db.Column(db.String(255), nullable=False, unique=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow)

    user = db.relationship("User", backref=db.backref("wearable_steps", passive_deletes=True))
    source = db.relationship("WearableSource", backref=db.backref("canonical_steps", passive_deletes=True))
    raw = db.relationship("WearableRaw", backref=db.backref("canonical_steps", passive_deletes=True))


class WearableCanonicalHR(db.Model):
    __tablename__ = "wearable_canonical_hr"
    __table_args__ = (
        db.UniqueConstraint("dedupe_key", name="uq_wearable_canonical_hr_dedupe_key"),
        db.Index("ix_wearable_canonical_hr_user_timestamp", "user_id", "timestamp_utc"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_id = db.Column(
        db.Integer,
        db.ForeignKey("wearable_sources.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    raw_id = db.Column(
        db.Integer,
        db.ForeignKey("wearable_raw.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    timestamp_utc = db.Column(db.DateTime(timezone=True), nullable=False)
    bpm = db.Column(db.Integer, nullable=False)
    confidence = db.Column(db.String(32), nullable=True)
    variability_ms = db.Column(db.Float, nullable=True)
    dedupe_key = db.Column(db.String(255), nullable=False, unique=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow)

    user = db.relationship("User", backref=db.backref("wearable_hr", passive_deletes=True))
    source = db.relationship("WearableSource", backref=db.backref("canonical_hr", passive_deletes=True))
    raw = db.relationship("WearableRaw", backref=db.backref("canonical_hr", passive_deletes=True))


class WearableCanonicalSleepSession(db.Model):
    __tablename__ = "wearable_canonical_sleep_sessions"
    __table_args__ = (
        db.UniqueConstraint("dedupe_key", name="uq_wearable_canonical_sleep_sessions_dedupe_key"),
        db.Index("ix_wearable_sleep_sessions_user_start", "user_id", "start_time_utc"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_id = db.Column(
        db.Integer,
        db.ForeignKey("wearable_sources.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    raw_id = db.Column(
        db.Integer,
        db.ForeignKey("wearable_raw.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    start_time_utc = db.Column(db.DateTime(timezone=True), nullable=False)
    end_time_utc = db.Column(db.DateTime(timezone=True), nullable=False)
    duration_seconds = db.Column(db.Integer, nullable=True)
    sleep_type = db.Column(db.String(32), nullable=True)
    score = db.Column(db.Integer, nullable=True)
    dedupe_key = db.Column(db.String(255), nullable=False, unique=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow)

    user = db.relationship("User", backref=db.backref("wearable_sleep_sessions", passive_deletes=True))
    source = db.relationship("WearableSource", backref=db.backref("sleep_sessions", passive_deletes=True))
    raw = db.relationship("WearableRaw", backref=db.backref("sleep_sessions", passive_deletes=True))


class WearableCanonicalSleepStage(db.Model):
    __tablename__ = "wearable_canonical_sleep_stages"
    __table_args__ = (
        db.UniqueConstraint("dedupe_key", name="uq_wearable_canonical_sleep_stages_dedupe_key"),
        db.Index("ix_wearable_sleep_stages_user_start", "user_id", "start_time_utc"),
    )

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(
        db.Integer,
        db.ForeignKey("wearable_canonical_sleep_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    stage_type = db.Column(db.String(32), nullable=False)
    start_time_utc = db.Column(db.DateTime(timezone=True), nullable=False)
    end_time_utc = db.Column(db.DateTime(timezone=True), nullable=False)
    duration_seconds = db.Column(db.Integer, nullable=True)
    dedupe_key = db.Column(db.String(255), nullable=False, unique=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow)

    session = db.relationship(
        "WearableCanonicalSleepSession",
        backref=db.backref("stages", passive_deletes=True),
    )
    user = db.relationship("User", backref=db.backref("wearable_sleep_stages", passive_deletes=True))


class WearableDailyAgg(db.Model):
    __tablename__ = "wearable_daily_agg"
    __table_args__ = (
        db.UniqueConstraint("dedupe_key", name="uq_wearable_daily_agg_dedupe_key"),
        db.Index("ix_wearable_daily_agg_user_day", "user_id", "day_start_utc"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_id = db.Column(
        db.Integer,
        db.ForeignKey("wearable_sources.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    day_start_utc = db.Column(db.DateTime(timezone=True), nullable=False)
    steps = db.Column(db.Integer, nullable=True)
    distance_meters = db.Column(db.Float, nullable=True)
    calories = db.Column(db.Float, nullable=True)
    resting_heart_rate = db.Column(db.Integer, nullable=True)
    hrv_rmssd_ms = db.Column(db.Float, nullable=True)
    sleep_seconds = db.Column(db.Integer, nullable=True)
    payload = db.Column(db.JSON, nullable=True)
    dedupe_key = db.Column(db.String(255), nullable=False, unique=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow)

    user = db.relationship("User", backref=db.backref("wearable_daily_agg", passive_deletes=True))
    source = db.relationship("WearableSource", backref=db.backref("daily_aggregates", passive_deletes=True))


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
