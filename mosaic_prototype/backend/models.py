from datetime import datetime

from extensions import db


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

    def __repr__(self) -> str:  # pragma: no cover - convenience
        return f"<Entry {self.date} {self.activity}>"


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self) -> str:  # pragma: no cover - convenience
        return f"<User {self.username}>"
