import sqlite3
from pathlib import Path

import pytest

from app import app


@pytest.fixture()
def client(tmp_path):
    db_path = tmp_path / "test.db"
    schema_path = Path(__file__).resolve().parents[2] / "database" / "schema.sql"

    schema_sql = schema_path.read_text(encoding="utf-8")
    conn = sqlite3.connect(db_path)
    conn.executescript(schema_sql)
    conn.commit()
    conn.close()

    app.config.update(
        {
            "TESTING": True,
            "DB_PATH": str(db_path),
        }
    )

    with app.test_client() as client:
        yield client


@pytest.fixture()
def db_conn():
    conn = sqlite3.connect(app.config["DB_PATH"])
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()
