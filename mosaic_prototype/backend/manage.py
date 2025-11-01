"""Management helpers for database migrations.

Provides convenience commands for initializing the migrations folder,
generating new revisions and applying them. Wraps Flask-Migrate so the
project can run migrations without invoking the Flask CLI directly.
"""

from pathlib import Path

import click
from flask_migrate import init as flask_migrate_init # type: ignore[import]
from flask_migrate import migrate as flask_migrate_migrate # type: ignore[import]
from flask_migrate import upgrade as flask_migrate_upgrade # type: ignore[import]

from app import app

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


if __name__ == "__main__":
    cli()
