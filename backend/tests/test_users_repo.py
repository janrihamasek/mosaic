from datetime import datetime

import pytest
from app import app
from extensions import db
from repositories import users_repo


@pytest.mark.usefixtures("client")
def test_users_repo_crud():
    with app.app_context():
        username = f"user_{datetime.utcnow().timestamp()}"
        user_id = users_repo.create_user(
            username, "hash", username, datetime.utcnow().isoformat()
        )
        assert user_id > 0

        row = users_repo.get_user_by_username(username)
        assert row is not None
        assert row["id"] == user_id

        users_repo.update_user(user_id, {"display_name": "Updated"})
        updated = users_repo.get_user_by_id(user_id)
        assert updated is not None
        assert updated["display_name"] == "Updated"

        count = users_repo.delete_user(user_id)
        assert count == 1
        db.session.commit()
