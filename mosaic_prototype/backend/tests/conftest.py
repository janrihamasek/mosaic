import os

import pytest

from app import app
from extensions import db
from sqlalchemy import text
from security import rate_limiter


@pytest.fixture()
def client():
    database_url = (
        os.environ.get("TEST_DATABASE_URL")
        or os.environ.get("DATABASE_URL")
        or "postgresql+psycopg2://postgres:postgres@localhost:5432/mosaic_test"
    )

    app.config.update(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": database_url,
            "API_KEY": None,
        }
    )

    try:
        with app.app_context():
            db.session.remove()
            db.engine.dispose()
            connection = db.engine.connect()
            connection.close()
            db.session.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
            db.session.execute(text("CREATE SCHEMA public"))
            db.session.commit()
            db.create_all()
            db.session.commit()
    except Exception as exc:  # pragma: no cover - skip if database unavailable
        pytest.skip(f"PostgreSQL database not available: {exc}")

    rate_limiter._calls.clear()  # type: ignore[attr-defined]

    with app.test_client() as client:
        yield client

    with app.app_context():
        db.session.remove()
        db.session.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
        db.session.execute(text("CREATE SCHEMA public"))
        db.session.commit()
        db.engine.dispose()
