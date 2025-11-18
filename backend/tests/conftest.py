import os

import pytest
from app import app
from extensions import db
from infra import rate_limiter, cache_manager
import importlib
from sqlalchemy import text


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

    rate_limiter.reset()
    cache_manager.reset_cache()
    cache_manager.set_time_provider(lambda: importlib.import_module("app").time())

    with app.test_client() as client:
        yield client

    with app.app_context():
        db.session.remove()
        db.session.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
        db.session.execute(text("CREATE SCHEMA public"))
        db.session.commit()
        db.engine.dispose()
