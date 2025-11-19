"""Repository helpers for health checks."""

from sqlalchemy import text

from extensions import db


def check_database_connection() -> bool:
    """Execute a lightweight database ping."""
    with db.engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return True
