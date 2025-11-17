from contextlib import contextmanager

from flask_migrate import Migrate  # type: ignore[import]
from flask_sqlalchemy import SQLAlchemy  # type: ignore[import]

from db_utils import transactional_connection

db = SQLAlchemy()
migrate = Migrate()


@contextmanager
def db_transaction():
    """Context manager yielding a transactional DB connection."""
    with transactional_connection(db.engine) as conn:
        yield conn

# Expose helper as a method on the SQLAlchemy extension for convenience.
db.db_transaction = db_transaction
