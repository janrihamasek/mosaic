"""Add activity_type column to entries."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20241205_000008"
down_revision = "20241205_000007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "entries",
        sa.Column(
            "activity_type",
            sa.String(length=16),
            nullable=False,
            server_default="positive",
        ),
    )


def downgrade() -> None:
    op.drop_column("entries", "activity_type")
