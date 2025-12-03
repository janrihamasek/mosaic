"""Make activities, entries, and backup_settings user-scoped."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20250108_000010"
down_revision = "20241226_000009"
branch_labels = None
depends_on = None


def _drop_table_if_exists(table_name: str) -> None:
    op.execute(sa.text(f'DROP TABLE IF EXISTS "{table_name}" CASCADE'))


def upgrade() -> None:
    # Drop the existing tables (expected empty DB) to rebuild with user scoping.
    for table in ("entries", "activities", "backup_settings"):
        _drop_table_if_exists(table)

    op.create_table(
        "activities",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column(
            "category", sa.String(length=120), nullable=False, server_default=""
        ),
        sa.Column("goal", sa.Float(), nullable=False, server_default="0"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "frequency_per_day", sa.Integer(), nullable=False, server_default="1"
        ),
        sa.Column(
            "frequency_per_week", sa.Integer(), nullable=False, server_default="1"
        ),
        sa.Column("deactivated_at", sa.String(length=32), nullable=True),
        sa.Column(
            "activity_type",
            sa.String(length=16),
            nullable=False,
            server_default="positive",
        ),
        sa.Column(
            "is_system",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.UniqueConstraint("user_id", "name", name="uq_activities_user_name"),
    )
    op.create_index("idx_activities_user_id", "activities", ["user_id"])
    op.create_index(
        "idx_activities_user_category", "activities", ["user_id", "category"]
    )

    op.create_table(
        "entries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("date", sa.String(length=10), nullable=False),
        sa.Column("activity", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("value", sa.Float(), nullable=True, server_default="0"),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "activity_category",
            sa.String(length=120),
            nullable=False,
            server_default="",
        ),
        sa.Column("activity_goal", sa.Float(), nullable=False, server_default="0"),
        sa.Column(
            "activity_type",
            sa.String(length=16),
            nullable=False,
            server_default="positive",
        ),
        sa.UniqueConstraint(
            "user_id", "date", "activity", name="uq_entries_user_date_activity"
        ),
    )
    op.create_index("idx_entries_user_id_date", "entries", ["user_id", "date"])
    op.create_index("idx_entries_user_id_activity", "entries", ["user_id", "activity"])
    op.create_index(
        "idx_entries_user_id_activity_category",
        "entries",
        ["user_id", "activity_category"],
    )

    op.create_table(
        "backup_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "enabled", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column(
            "interval_minutes", sa.Integer(), nullable=False, server_default="60"
        ),
        sa.Column("last_run", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("user_id", name="uq_backup_settings_user_id"),
    )


def downgrade() -> None:
    # Drop the user-scoped versions and recreate the previous schema.
    for table in ("entries", "activities", "backup_settings"):
        _drop_table_if_exists(table)

    op.create_table(
        "activities",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False, unique=True),
        sa.Column(
            "category", sa.String(length=120), nullable=False, server_default=""
        ),
        sa.Column("goal", sa.Float(), nullable=False, server_default="0"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "frequency_per_day", sa.Integer(), nullable=False, server_default="1"
        ),
        sa.Column(
            "frequency_per_week", sa.Integer(), nullable=False, server_default="1"
        ),
        sa.Column("deactivated_at", sa.String(length=32), nullable=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "activity_type",
            sa.String(length=16),
            nullable=False,
            server_default="positive",
        ),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default="0"),
    )
    op.create_index("idx_activities_category", "activities", ["category"])
    op.create_index("ix_activities_user_id", "activities", ["user_id"])

    op.create_table(
        "entries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("date", sa.String(length=10), nullable=False),
        sa.Column("activity", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("value", sa.Float(), nullable=True, server_default="0"),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "activity_category",
            sa.String(length=120),
            nullable=False,
            server_default="",
        ),
        sa.Column("activity_goal", sa.Float(), nullable=False, server_default="0"),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "activity_type",
            sa.String(length=16),
            nullable=False,
            server_default="positive",
        ),
    )
    op.create_index("idx_entries_date", "entries", ["date"])
    op.create_index("idx_entries_activity", "entries", ["activity"])
    op.create_index(
        "idx_entries_activity_category", "entries", ["activity_category"]
    )
    op.create_index("ix_entries_user_id", "entries", ["user_id"])

    op.create_table(
        "backup_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "enabled", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column(
            "interval_minutes", sa.Integer(), nullable=False, server_default="60"
        ),
        sa.Column("last_run", sa.DateTime(timezone=True), nullable=True),
    )
