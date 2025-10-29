import sqlite3
from pathlib import Path

import pytest

from app import app, configure_database_path
from security import rate_limiter


@pytest.fixture()
def client(tmp_path):
    db_path = tmp_path / "test.db"
    schema_path = Path(__file__).resolve().parents[2] / "database" / "schema.sql"

    schema_sql = schema_path.read_text(encoding="utf-8")
    conn = sqlite3.connect(db_path)
    conn.executescript(schema_sql)
    conn.commit()
    conn.close()

    rate_limiter._calls.clear()  # type: ignore[attr-defined]

    app.config.update(
        {
            "TESTING": True,
            "DB_PATH": str(db_path),
            "API_KEY": None,
            "_SCHEMA_READY": False,
        }
    )
    configure_database_path(str(db_path))

    with app.test_client() as client:
        yield client
