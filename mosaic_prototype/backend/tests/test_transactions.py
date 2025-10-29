import sqlite3
from pathlib import Path

import pytest

from app import app
from import_data import import_csv


def test_import_csv_rolls_back_on_failure(tmp_path, client, monkeypatch):
    csv_path = tmp_path / "rollback.csv"
    csv_path.write_text(
        "date,activity,value,note,description,category,goal\n"
        "2024-03-01,Swim,2,,Morning swim,Fitness,12\n",
        encoding="utf-8",
    )

    original_connect = sqlite3.connect

    class FailingConnection(sqlite3.Connection):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._failure_triggered = False

        def execute(self, sql, *args, **kwargs):
            result = super().execute(sql, *args, **kwargs)
            if "INSERT INTO entries" in sql and not self._failure_triggered:
                self._failure_triggered = True
                raise RuntimeError("Simulated failure after insert")
            return result

    def failing_connect(*args, **kwargs):
        kwargs.setdefault("factory", FailingConnection)
        return original_connect(*args, **kwargs)

    monkeypatch.setattr(sqlite3, "connect", failing_connect)

    db_path = Path(app.config["DB_PATH"])
    assert db_path.exists()

    with pytest.raises(RuntimeError):
        import_csv(str(csv_path), db_path=str(db_path))

    conn = sqlite3.connect(db_path)
    try:
        count = conn.execute("SELECT COUNT(*) FROM entries").fetchone()[0]
        assert count == 0
    finally:
        conn.close()
