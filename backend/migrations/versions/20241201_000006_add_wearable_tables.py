"""Create wearable ingestion and analytics tables."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20241201_000006"
down_revision = "20241125_000005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "wearable_sources",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("external_id", sa.String(length=128), nullable=False),
        sa.Column("display_name", sa.String(length=128), nullable=True),
        sa.Column("sync_metadata", sa.JSON(), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("dedupe_key", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("dedupe_key", name="uq_wearable_sources_dedupe_key"),
        sa.UniqueConstraint(
            "user_id",
            "provider",
            "external_id",
            name="uq_wearable_sources_user_provider_external",
        ),
    )
    op.create_index("ix_wearable_sources_user_id", "wearable_sources", ["user_id"])

    op.create_table(
        "wearable_raw",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_id", sa.Integer(), sa.ForeignKey("wearable_sources.id", ondelete="CASCADE"), nullable=True),
        sa.Column("collected_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("received_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("dedupe_key", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("dedupe_key", name="uq_wearable_raw_dedupe_key"),
    )
    op.create_index("ix_wearable_raw_user_id", "wearable_raw", ["user_id"])
    op.create_index("ix_wearable_raw_source_id", "wearable_raw", ["source_id"])
    op.create_index(
        "ix_wearable_raw_user_collected_at",
        "wearable_raw",
        ["user_id", "collected_at_utc"],
    )

    op.create_table(
        "wearable_canonical_steps",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_id", sa.Integer(), sa.ForeignKey("wearable_sources.id", ondelete="SET NULL"), nullable=True),
        sa.Column("raw_id", sa.Integer(), sa.ForeignKey("wearable_raw.id", ondelete="SET NULL"), nullable=True),
        sa.Column("start_time_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_time_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("steps", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("distance_meters", sa.Float(), nullable=True),
        sa.Column("active_minutes", sa.Integer(), nullable=True),
        sa.Column("dedupe_key", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("dedupe_key", name="uq_wearable_canonical_steps_dedupe_key"),
    )
    op.create_index("ix_wearable_canonical_steps_user_id", "wearable_canonical_steps", ["user_id"])
    op.create_index("ix_wearable_canonical_steps_source_id", "wearable_canonical_steps", ["source_id"])
    op.create_index("ix_wearable_canonical_steps_raw_id", "wearable_canonical_steps", ["raw_id"])
    op.create_index(
        "ix_wearable_canonical_steps_user_start",
        "wearable_canonical_steps",
        ["user_id", "start_time_utc"],
    )

    op.create_table(
        "wearable_canonical_hr",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_id", sa.Integer(), sa.ForeignKey("wearable_sources.id", ondelete="SET NULL"), nullable=True),
        sa.Column("raw_id", sa.Integer(), sa.ForeignKey("wearable_raw.id", ondelete="SET NULL"), nullable=True),
        sa.Column("timestamp_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("bpm", sa.Integer(), nullable=False),
        sa.Column("confidence", sa.String(length=32), nullable=True),
        sa.Column("variability_ms", sa.Float(), nullable=True),
        sa.Column("dedupe_key", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("dedupe_key", name="uq_wearable_canonical_hr_dedupe_key"),
    )
    op.create_index("ix_wearable_canonical_hr_user_id", "wearable_canonical_hr", ["user_id"])
    op.create_index("ix_wearable_canonical_hr_source_id", "wearable_canonical_hr", ["source_id"])
    op.create_index("ix_wearable_canonical_hr_raw_id", "wearable_canonical_hr", ["raw_id"])
    op.create_index(
        "ix_wearable_canonical_hr_user_timestamp",
        "wearable_canonical_hr",
        ["user_id", "timestamp_utc"],
    )

    op.create_table(
        "wearable_canonical_sleep_sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_id", sa.Integer(), sa.ForeignKey("wearable_sources.id", ondelete="SET NULL"), nullable=True),
        sa.Column("raw_id", sa.Integer(), sa.ForeignKey("wearable_raw.id", ondelete="SET NULL"), nullable=True),
        sa.Column("start_time_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_time_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("sleep_type", sa.String(length=32), nullable=True),
        sa.Column("score", sa.Integer(), nullable=True),
        sa.Column("dedupe_key", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("dedupe_key", name="uq_wearable_canonical_sleep_sessions_dedupe_key"),
    )
    op.create_index("ix_wearable_canonical_sleep_sessions_user_id", "wearable_canonical_sleep_sessions", ["user_id"])
    op.create_index("ix_wearable_canonical_sleep_sessions_source_id", "wearable_canonical_sleep_sessions", ["source_id"])
    op.create_index("ix_wearable_canonical_sleep_sessions_raw_id", "wearable_canonical_sleep_sessions", ["raw_id"])
    op.create_index(
        "ix_wearable_sleep_sessions_user_start",
        "wearable_canonical_sleep_sessions",
        ["user_id", "start_time_utc"],
    )

    op.create_table(
        "wearable_canonical_sleep_stages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("session_id", sa.Integer(), sa.ForeignKey("wearable_canonical_sleep_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("stage_type", sa.String(length=32), nullable=False),
        sa.Column("start_time_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_time_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("dedupe_key", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("dedupe_key", name="uq_wearable_canonical_sleep_stages_dedupe_key"),
    )
    op.create_index("ix_wearable_canonical_sleep_stages_session_id", "wearable_canonical_sleep_stages", ["session_id"])
    op.create_index("ix_wearable_canonical_sleep_stages_user_id", "wearable_canonical_sleep_stages", ["user_id"])
    op.create_index(
        "ix_wearable_sleep_stages_user_start",
        "wearable_canonical_sleep_stages",
        ["user_id", "start_time_utc"],
    )

    op.create_table(
        "wearable_daily_agg",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_id", sa.Integer(), sa.ForeignKey("wearable_sources.id", ondelete="SET NULL"), nullable=True),
        sa.Column("day_start_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("steps", sa.Integer(), nullable=True),
        sa.Column("distance_meters", sa.Float(), nullable=True),
        sa.Column("calories", sa.Float(), nullable=True),
        sa.Column("resting_heart_rate", sa.Integer(), nullable=True),
        sa.Column("hrv_rmssd_ms", sa.Float(), nullable=True),
        sa.Column("sleep_seconds", sa.Integer(), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("dedupe_key", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("dedupe_key", name="uq_wearable_daily_agg_dedupe_key"),
    )
    op.create_index("ix_wearable_daily_agg_user_id", "wearable_daily_agg", ["user_id"])
    op.create_index("ix_wearable_daily_agg_source_id", "wearable_daily_agg", ["source_id"])
    op.create_index(
        "ix_wearable_daily_agg_user_day",
        "wearable_daily_agg",
        ["user_id", "day_start_utc"],
    )


def downgrade() -> None:
    op.drop_index("ix_wearable_daily_agg_user_day", table_name="wearable_daily_agg")
    op.drop_index("ix_wearable_daily_agg_source_id", table_name="wearable_daily_agg")
    op.drop_index("ix_wearable_daily_agg_user_id", table_name="wearable_daily_agg")
    op.drop_table("wearable_daily_agg")

    op.drop_index("ix_wearable_sleep_stages_user_start", table_name="wearable_canonical_sleep_stages")
    op.drop_index("ix_wearable_canonical_sleep_stages_user_id", table_name="wearable_canonical_sleep_stages")
    op.drop_index("ix_wearable_canonical_sleep_stages_session_id", table_name="wearable_canonical_sleep_stages")
    op.drop_table("wearable_canonical_sleep_stages")

    op.drop_index("ix_wearable_sleep_sessions_user_start", table_name="wearable_canonical_sleep_sessions")
    op.drop_index("ix_wearable_canonical_sleep_sessions_raw_id", table_name="wearable_canonical_sleep_sessions")
    op.drop_index("ix_wearable_canonical_sleep_sessions_source_id", table_name="wearable_canonical_sleep_sessions")
    op.drop_index("ix_wearable_canonical_sleep_sessions_user_id", table_name="wearable_canonical_sleep_sessions")
    op.drop_table("wearable_canonical_sleep_sessions")

    op.drop_index("ix_wearable_canonical_hr_user_timestamp", table_name="wearable_canonical_hr")
    op.drop_index("ix_wearable_canonical_hr_raw_id", table_name="wearable_canonical_hr")
    op.drop_index("ix_wearable_canonical_hr_source_id", table_name="wearable_canonical_hr")
    op.drop_index("ix_wearable_canonical_hr_user_id", table_name="wearable_canonical_hr")
    op.drop_table("wearable_canonical_hr")

    op.drop_index("ix_wearable_canonical_steps_user_start", table_name="wearable_canonical_steps")
    op.drop_index("ix_wearable_canonical_steps_raw_id", table_name="wearable_canonical_steps")
    op.drop_index("ix_wearable_canonical_steps_source_id", table_name="wearable_canonical_steps")
    op.drop_index("ix_wearable_canonical_steps_user_id", table_name="wearable_canonical_steps")
    op.drop_table("wearable_canonical_steps")

    op.drop_index("ix_wearable_raw_user_collected_at", table_name="wearable_raw")
    op.drop_index("ix_wearable_raw_source_id", table_name="wearable_raw")
    op.drop_index("ix_wearable_raw_user_id", table_name="wearable_raw")
    op.drop_table("wearable_raw")

    op.drop_index("ix_wearable_sources_user_id", table_name="wearable_sources")
    op.drop_table("wearable_sources")
