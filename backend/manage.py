"""Management helpers for database migrations.

Provides convenience commands for initializing the migrations folder,
generating new revisions and applying them. Wraps Flask-Migrate so the
project can run migrations without invoking the Flask CLI directly.
"""

from __future__ import annotations

import json
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from time import perf_counter
from typing import Optional

import click

# Ensure models are imported so Flask-Migrate sees them
import models  # noqa: F401
import sqlalchemy as sa
import structlog
from agg_jobs import rebuild_daily_aggregates_for_user
from app import app
from extensions import db
from flask_migrate import init as flask_migrate_init  # type: ignore[import]
from flask_migrate import migrate as flask_migrate_migrate  # type: ignore[import]
from flask_migrate import upgrade as flask_migrate_upgrade  # type: ignore[import]
from models import (
    User,
    WearableCanonicalHR,
    WearableCanonicalSleepSession,
    WearableCanonicalSteps,
    WearableDailyAgg,
)
from sqlalchemy import func

logger = structlog.get_logger("mosaic.manage")
MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"


@click.group()
def cli():
    """Manage database migrations."""


@cli.command("init")
def init_command():
    """Initialise the migrations directory if it does not exist."""

    if MIGRATIONS_DIR.exists():
        click.echo("Migrations directory already exists – skipping initialization.")
        return

    with app.app_context():
        flask_migrate_init(directory=str(MIGRATIONS_DIR))
    click.echo(f"Initialized migrations folder at {MIGRATIONS_DIR}")


@cli.command("migrate")
@click.option("--message", "-m", default="auto", help="Migration message")
def migrate_command(message: str):
    """Generate a new migration based on current models."""

    if not MIGRATIONS_DIR.exists():
        raise click.ClickException("Migrations directory missing – run 'init' first.")

    with app.app_context():
        flask_migrate_migrate(directory=str(MIGRATIONS_DIR), message=message or "auto")
    click.echo("Migration script generated in migrations/versions.")


@cli.command("upgrade")
@click.option("--revision", default="head", help="Target revision (default: head)")
def upgrade_command(revision: str):
    """Apply migrations up to the selected revision."""

    if not MIGRATIONS_DIR.exists():
        raise click.ClickException("Migrations directory missing – run 'init' first.")

    with app.app_context():
        flask_migrate_upgrade(directory=str(MIGRATIONS_DIR), revision=revision)
    click.echo(f"Database upgraded to revision {revision}.")


@cli.command("assign-user-data")
@click.option("--username", required=True, help="Existing username to own legacy data.")
@click.option(
    "--make-admin/--no-admin",
    default=True,
    show_default=True,
    help="Grant admin role to the user.",
)
def assign_user_data(username: str, make_admin: bool) -> None:
    """Assign existing activities/entries without owners to a specific user."""

    with app.app_context():
        session = db.session
        try:
            user_row = session.execute(
                sa.text("SELECT id FROM users WHERE username = :username"),
                {"username": username},
            ).fetchone()
            if not user_row:
                raise click.ClickException(f"User '{username}' not found.")

            user_id = user_row[0]

            if make_admin:
                session.execute(
                    sa.text("UPDATE users SET is_admin = TRUE WHERE id = :user_id"),
                    {"user_id": user_id},
                )

            updated_activities = int(
                session.execute(
                    sa.text(
                        "UPDATE activities SET user_id = :user_id WHERE user_id IS NULL"
                    ),
                    {"user_id": user_id},
                ).rowcount
                or 0
            )

            updated_entries = int(
                session.execute(
                    sa.text(
                        "UPDATE entries SET user_id = :user_id WHERE user_id IS NULL"
                    ),
                    {"user_id": user_id},
                ).rowcount
                or 0
            )

            session.commit()
        except Exception as exc:
            session.rollback()
            raise click.ClickException(f"Failed to assign data: {exc}") from exc
        else:
            click.echo(
                f"User '{username}' (id={user_id}) updated. "
                f"Activities assigned: {updated_activities}, Entries assigned: {updated_entries}. "
                f"Admin granted: {'yes' if make_admin else 'no'}."
            )


def _resolve_user_ids(
    session, *, user_id: Optional[int], username: Optional[str], all_users: bool
) -> list[int]:
    if all_users:
        return [row[0] for row in session.execute(sa.select(User.id)).all()]
    if username:
        user_row = session.execute(
            sa.text("SELECT id FROM users WHERE username = :username"),
            {"username": username},
        ).fetchone()
        if not user_row:
            raise click.ClickException(f"User '{username}' not found.")
        return [user_row[0]]
    if user_id is not None:
        return [user_id]
    raise click.ClickException("Specify --user-id/--username or --all-users.")


@cli.command("rebuild-wearable-agg")
@click.option("--user-id", type=int, help="Rebuild aggregates for a specific user.")
@click.option("--username", help="Rebuild aggregates for this username.")
@click.option(
    "--all-users",
    is_flag=True,
    default=False,
    help="Rebuild aggregates for every user.",
)
@click.option(
    "--start-date",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    default=None,
    help="Start date (inclusive) in YYYY-MM-DD format (defaults to today).",
)
@click.option(
    "--end-date",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    default=None,
    help="End date (inclusive) in YYYY-MM-DD format (defaults to start date).",
)
def rebuild_wearable_agg(
    user_id: Optional[int],
    username: Optional[str],
    all_users: bool,
    start_date: Optional[datetime],
    end_date: Optional[datetime],
) -> None:
    """Rebuild wearable daily aggregates for users and date ranges."""

    target_start = start_date.date() if start_date else date.today()
    target_end = end_date.date() if end_date else target_start
    if target_end < target_start:
        raise click.ClickException("end-date cannot be before start-date.")

    with app.app_context():
        session = db.session
        ids = _resolve_user_ids(
            session, user_id=user_id, username=username, all_users=all_users
        )
        start_time = perf_counter()
        for uid in ids:
            rebuild_daily_aggregates_for_user(
                user_id=uid, start_date=target_start, end_date=target_end
            )
        duration = perf_counter() - start_time
        session.expire_all()

        start_dt = datetime.combine(target_start, time.min).replace(tzinfo=timezone.utc)
        end_dt = datetime.combine(target_end + timedelta(days=1), time.min).replace(
            tzinfo=timezone.utc
        )

        rows_updated = (
            session.query(WearableDailyAgg)
            .filter(WearableDailyAgg.user_id.in_(ids))
            .filter(
                WearableDailyAgg.day_start_utc >= start_dt,
                WearableDailyAgg.day_start_utc < end_dt,
            )
            .count()
        )

        steps_total = session.execute(
            sa.select(func.coalesce(func.sum(WearableCanonicalSteps.steps), 0)).where(
                WearableCanonicalSteps.user_id.in_(ids),
                WearableCanonicalSteps.start_time_utc < end_dt,
                WearableCanonicalSteps.end_time_utc >= start_dt,
            )
        ).scalar_one()

        sleep_seconds = session.execute(
            sa.select(
                func.coalesce(
                    func.sum(WearableCanonicalSleepSession.duration_seconds), 0
                )
            ).where(
                WearableCanonicalSleepSession.user_id.in_(ids),
                WearableCanonicalSleepSession.start_time_utc < end_dt,
                WearableCanonicalSleepSession.end_time_utc >= start_dt,
            )
        ).scalar_one()

        avg_hr = session.execute(
            sa.select(func.avg(WearableCanonicalHR.bpm)).where(
                WearableCanonicalHR.user_id.in_(ids),
                WearableCanonicalHR.timestamp_utc >= start_dt,
                WearableCanonicalHR.timestamp_utc < end_dt,
            )
        ).scalar_one()

        sleep_minutes = round((sleep_seconds or 0) / 60, 2)
        avg_hr_value = float(avg_hr) if avg_hr is not None else None
        summary = {
            "rows_updated": rows_updated,
            "steps_total": int(steps_total or 0),
            "sleep_minutes_total": sleep_minutes,
            "avg_heart_rate": avg_hr_value,
            "duration_s": round(duration, 2),
        }
        logger.info(
            "wearable.agg_rebuild",
            user_ids=ids,
            start=target_start.isoformat(),
            end=target_end.isoformat(),
            summary=summary,
        )
        click.echo(json.dumps(summary))


if __name__ == "__main__":
    cli()
