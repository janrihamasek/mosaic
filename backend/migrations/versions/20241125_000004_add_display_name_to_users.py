"""Add display_name column to users."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20241125_000004"
down_revision = "20241125_000003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("users"):
        return

    columns = {col["name"] for col in inspector.get_columns("users")}
    if "display_name" not in columns:
        op.add_column(
            "users",
            sa.Column("display_name", sa.String(length=120), nullable=False, server_default=""),
        )
        op.execute("UPDATE users SET display_name = username WHERE COALESCE(display_name, '') = ''")
        op.alter_column("users", "display_name", server_default=None)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table("users"):
        columns = {col["name"] for col in inspector.get_columns("users")}
        if "display_name" in columns:
            op.drop_column("users", "display_name")
