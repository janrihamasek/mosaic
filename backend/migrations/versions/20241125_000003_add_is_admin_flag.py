"""Add is_admin flag to users table."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20241125_000003"
down_revision = "20241125_000002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("users"):
        return

    existing_columns = {col["name"] for col in inspector.get_columns("users")}
    if "is_admin" not in existing_columns:
        op.add_column(
            "users",
            sa.Column(
                "is_admin", sa.Boolean(), nullable=False, server_default=sa.false()
            ),
        )
        op.execute("UPDATE users SET is_admin = FALSE WHERE is_admin IS NULL")
        op.alter_column("users", "is_admin", server_default=None)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table("users"):
        existing_columns = {col["name"] for col in inspector.get_columns("users")}
        if "is_admin" in existing_columns:
            op.drop_column("users", "is_admin")
