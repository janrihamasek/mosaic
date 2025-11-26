"""Add neutral to activity_type and is_system flag.

This migration:
1. No SQLite constraints to modify (SQLite doesn't support ALTER CHECK)
2. Adds is_system boolean column to activities
3. Creates Mood system category and activity for all users
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20241226_000009"
down_revision = "20241205_000008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add is_system column to activities
    op.add_column(
        "activities",
        sa.Column(
            "is_system",
            sa.Boolean(),
            nullable=False,
            server_default="0",
        ),
    )

    # Create Mood system activity (globally, due to unique constraint on name)
    conn = op.get_bind()
    
    # Check if Mood activity already exists (global check due to unique constraint)
    existing = conn.execute(
        sa.text("SELECT id FROM activities WHERE name = :name"),
        {"name": "Mood"}
    ).fetchone()
    
    if not existing:
        # Get first user to assign Mood activity to
        first_user = conn.execute(sa.text("SELECT id FROM users ORDER BY id LIMIT 1")).fetchone()
        
        if first_user:
            # Insert Mood activity for first user
            conn.execute(
                sa.text(
                    """
                    INSERT INTO activities 
                    (name, category, activity_type, goal, active, is_system, user_id)
                    VALUES 
                    (:name, :category, :activity_type, :goal, :active, :is_system, :user_id)
                    """
                ),
                {
                    "name": "Mood",
                    "category": "Mood",
                    "activity_type": "neutral",
                    "goal": 0.0,
                    "active": True,
                    "is_system": True,
                    "user_id": first_user[0]
                }
            )
    else:
        # If Mood exists, just mark it as system activity
        conn.execute(
            sa.text("UPDATE activities SET is_system = 1 WHERE name = 'Mood'")
        )


def downgrade() -> None:
    # Remove Mood activities
    conn = op.get_bind()
    conn.execute(
        sa.text("DELETE FROM activities WHERE name = 'Mood' AND is_system = 1")
    )
    
    # Drop is_system column
    op.drop_column("activities", "is_system")
