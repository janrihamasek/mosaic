"""Management helpers for database migrations.

Provides convenience commands for initializing the migrations folder,
generating new revisions and applying them. Wraps Flask-Migrate so the
project can run migrations without invoking the Flask CLI directly.
"""

from pathlib import Path

import click
import sqlalchemy as sa
from flask_migrate import init as flask_migrate_init # type: ignore[import]
from flask_migrate import migrate as flask_migrate_migrate # type: ignore[import]
from flask_migrate import upgrade as flask_migrate_upgrade # type: ignore[import]

from app import app
from extensions import db

# Ensure models are imported so Flask-Migrate sees them
import models  # noqa: F401


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
@click.option("--make-admin/--no-admin", default=True, show_default=True, help="Grant admin role to the user.")
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

            updated_activities = session.execute(
                sa.text("UPDATE activities SET user_id = :user_id WHERE user_id IS NULL"),
                {"user_id": user_id},
            ).rowcount

            updated_entries = session.execute(
                sa.text("UPDATE entries SET user_id = :user_id WHERE user_id IS NULL"),
                {"user_id": user_id},
            ).rowcount

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



if __name__ == "__main__":
    cli()
