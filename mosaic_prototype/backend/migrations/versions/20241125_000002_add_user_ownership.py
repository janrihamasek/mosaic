"""Add user ownership to activities and entries."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.engine.reflection import Inspector


revision = "20241125_000002"
down_revision = "20241115_000001"
branch_labels = None
depends_on = None


def _column_exists(inspector: Inspector, table_name: str, column_name: str) -> bool:
    if not inspector.has_table(table_name):
        return False
    return any(col["name"] == column_name for col in inspector.get_columns(table_name))


def _index_exists(inspector: Inspector, table_name: str, index_name: str) -> bool:
    if not inspector.has_table(table_name):
        return False
    return any(index["name"] == index_name for index in inspector.get_indexes(table_name))


def _foreign_key_exists(inspector: Inspector, table_name: str, constraint_name: str) -> bool:
    if not inspector.has_table(table_name):
        return False
    return any(fk["name"] == constraint_name for fk in inspector.get_foreign_keys(table_name))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("activities"):
        if not _column_exists(inspector, "activities", "user_id"):
            op.add_column("activities", sa.Column("user_id", sa.Integer(), nullable=True))
        if not _index_exists(inspector, "activities", "ix_activities_user_id"):
            op.create_index("ix_activities_user_id", "activities", ["user_id"])
        if inspector.has_table("users") and not _foreign_key_exists(
            inspector, "activities", "fk_activities_user_id_users"
        ):
            op.create_foreign_key(
                "fk_activities_user_id_users",
                "activities",
                "users",
                ["user_id"],
                ["id"],
                ondelete="CASCADE",
            )

    if inspector.has_table("entries"):
        if not _column_exists(inspector, "entries", "user_id"):
            op.add_column("entries", sa.Column("user_id", sa.Integer(), nullable=True))
        if not _index_exists(inspector, "entries", "ix_entries_user_id"):
            op.create_index("ix_entries_user_id", "entries", ["user_id"])
        if inspector.has_table("users") and not _foreign_key_exists(
            inspector, "entries", "fk_entries_user_id_users"
        ):
            op.create_foreign_key(
                "fk_entries_user_id_users",
                "entries",
                "users",
                ["user_id"],
                ["id"],
                ondelete="CASCADE",
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _foreign_key_exists(inspector, "entries", "fk_entries_user_id_users"):
        op.drop_constraint("fk_entries_user_id_users", "entries", type_="foreignkey")
    if _index_exists(inspector, "entries", "ix_entries_user_id"):
        op.drop_index("ix_entries_user_id", table_name="entries")
    if _column_exists(inspector, "entries", "user_id"):
        op.drop_column("entries", "user_id")

    if _foreign_key_exists(inspector, "activities", "fk_activities_user_id_users"):
        op.drop_constraint("fk_activities_user_id_users", "activities", type_="foreignkey")
    if _index_exists(inspector, "activities", "ix_activities_user_id"):
        op.drop_index("ix_activities_user_id", table_name="activities")
    if _column_exists(inspector, "activities", "user_id"):
        op.drop_column("activities", "user_id")
