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
