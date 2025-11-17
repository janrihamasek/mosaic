from contextlib import contextmanager
from typing import Iterator

from db_utils import connection as sa_connection, transactional_connection
from extensions import db


def get_db_connection():
    """Obtain a SQLAlchemy connection bound to the configured engine."""
    return sa_connection(db.engine)


@contextmanager
def db_transaction() -> Iterator:
    """Context manager yielding a transactional connection."""
    with transactional_connection(db.engine) as conn:
        yield conn
