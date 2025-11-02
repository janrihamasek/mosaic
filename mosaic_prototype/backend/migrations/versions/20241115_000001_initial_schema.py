"""Initial PostgreSQL schema for Mosaic."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20241115_000001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "activities",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False, unique=True),
        sa.Column("category", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("goal", sa.Float(), nullable=False, server_default="0"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("frequency_per_day", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("frequency_per_week", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("deactivated_at", sa.String(length=32), nullable=True),
    )
    op.create_index("idx_activities_category", "activities", ["category"])

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("username", sa.String(length=80), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "backup_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("interval_minutes", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("last_run", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "entries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("date", sa.String(length=10), nullable=False),
        sa.Column("activity", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("value", sa.Float(), nullable=True, server_default="0"),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("activity_category", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("activity_goal", sa.Float(), nullable=False, server_default="0"),
    )
    op.create_index("idx_entries_date", "entries", ["date"])
    op.create_index("idx_entries_activity", "entries", ["activity"])
    op.create_index("idx_entries_activity_category", "entries", ["activity_category"])


def downgrade() -> None:
    op.drop_index("idx_entries_activity_category", table_name="entries")
    op.drop_index("idx_entries_activity", table_name="entries")
    op.drop_index("idx_entries_date", table_name="entries")
    op.drop_table("entries")
    op.drop_table("backup_settings")
    op.drop_table("users")
    op.drop_index("idx_activities_category", table_name="activities")
    op.drop_table("activities")
