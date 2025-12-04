"""Ensure Mood system activity exists per user."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20250115_000011"
down_revision = "20250108_000010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # Mark existing Mood rows as system activities with neutral type/goal.
    conn.execute(
        sa.text(
            """
            UPDATE activities
            SET
                is_system = TRUE,
                activity_type = 'neutral',
                goal = 0.0,
                category = CASE
                    WHEN COALESCE(category, '') = '' THEN 'Mood'
                    ELSE category
                END
            WHERE LOWER(name) = 'mood'
            """
        )
    )

    # Insert Mood for users that do not have it yet.
    conn.execute(
        sa.text(
            """
            INSERT INTO activities (
                name,
                category,
                activity_type,
                goal,
                description,
                active,
                frequency_per_day,
                frequency_per_week,
                deactivated_at,
                user_id,
                is_system
            )
            SELECT
                'Mood',
                'Mood',
                'neutral',
                0.0,
                NULL,
                TRUE,
                1,
                7,
                NULL,
                u.id,
                TRUE
            FROM users u
            WHERE NOT EXISTS (
                SELECT 1 FROM activities a
                WHERE a.user_id = u.id
                  AND LOWER(a.name) = 'mood'
            )
            """
        )
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text("DELETE FROM activities WHERE LOWER(name) = 'mood' AND is_system = TRUE")
    )
