import pytest
from app import app
from extensions import db
from import_data import import_csv
from models import Entry
from repositories import entries_repo
from sqlalchemy import func, select


def test_import_csv_rolls_back_on_failure(tmp_path, client, monkeypatch):
    csv_path = tmp_path / "rollback.csv"
    csv_path.write_text(
        "date,activity,value,note,description,category,goal\n"
        "2024-03-01,Swim,2,,Morning swim,Fitness,12\n",
        encoding="utf-8",
    )

    original_upsert = entries_repo._upsert_entry_for_import

    state = {"calls": 0}

    def failing_upsert(parsed_row, activity_row, user_id, conn):
        state["calls"] += 1
        if state["calls"] == 1:
            return original_upsert(parsed_row, activity_row, user_id, conn)
        raise RuntimeError("Simulated failure after first upsert")

    monkeypatch.setattr(entries_repo, "_upsert_entry_for_import", failing_upsert)

    with pytest.raises(RuntimeError):
        import_csv(str(csv_path))

    with app.app_context():
        total = db.session.execute(select(func.count()).select_from(Entry)).scalar()
        assert total == 0
