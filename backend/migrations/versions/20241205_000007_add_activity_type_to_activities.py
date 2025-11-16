"""Add activity_type column to activities."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20241205_000007"
down_revision = "20241201_000006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "activities",
        sa.Column(
            "activity_type",
            sa.String(length=16),
            nullable=False,
            server_default="positive",
        ),
    )


def downgrade() -> None:
    op.drop_column("activities", "activity_type")
