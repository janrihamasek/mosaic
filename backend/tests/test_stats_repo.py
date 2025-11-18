from datetime import datetime

import pytest
from app import app
from extensions import db
from models import Activity, Entry
from repositories import stats_repo


@pytest.mark.usefixtures("client")
def test_get_today_entries_and_goals():
    with app.app_context():
        activity = Activity(
            name="Run",
            category="Health",
            activity_type="positive",
            goal=5.0,
            description="Morning run",
            active=True,
            frequency_per_day=1,
            frequency_per_week=7,
            user_id=1,
        )
        entry = Entry(
            date="2024-04-01",
            activity="Run",
            description="Morning run",
            value=3.0,
            note="good",
            activity_category="Health",
            activity_goal=5.0,
            activity_type="positive",
            user_id=1,
        )
        db.session.add_all([activity, entry])
        db.session.commit()

        rows = stats_repo.get_today_entries(1, False, "2024-04-01")
        assert len(rows) == 1
        assert rows[0]["goal"] == pytest.approx(5.0)
        assert rows[0]["category"] == "Health"

        goals = stats_repo.get_active_positive_goals_by_category(1, False)
        assert goals
        assert goals[0]["category"] == "Health"
        assert goals[0]["total_goal"] == pytest.approx(5.0)


@pytest.mark.usefixtures("client")
def test_daily_positive_totals():
    with app.app_context():
        entry1 = Entry(
            date="2024-04-01",
            activity="Yoga",
            description="",
            value=2.0,
            note="",
            activity_category="Wellness",
            activity_goal=2.0,
            activity_type="positive",
            user_id=2,
        )
        entry2 = Entry(
            date="2024-04-02",
            activity="Yoga",
            description="",
            value=1.0,
            note="",
            activity_category="Wellness",
            activity_goal=2.0,
            activity_type="positive",
            user_id=2,
        )
        db.session.add_all([entry1, entry2])
        db.session.commit()

        rows = stats_repo.get_daily_positive_totals(2, False, "2024-04-01", "2024-04-02")
        dates = {row["date"] for row in rows}
        assert {"2024-04-01", "2024-04-02"} <= dates
