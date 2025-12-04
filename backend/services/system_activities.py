"""
Helpers for provisioning system/default activities for users.
"""

from typing import Any, Dict, List

from audit import log_event
from repositories import activities_repo
from sqlalchemy.exc import SQLAlchemyError

# Extend this list as more default activities are introduced.
DEFAULT_SYSTEM_ACTIVITIES: List[Dict[str, Any]] = [
    {
        "name": "Mood",
        "category": "Mood",
        "activity_type": "neutral",
        "goal": 0.0,
        "description": None,
        "frequency_per_day": 1,
        "frequency_per_week": 7,
        "is_system": True,
    }
]


def ensure_default_system_activities(user_id: int) -> None:
    """
    Provision system activities for a user.

    Does not reactivate a previously deactivated system activity; it only ensures
    presence and correct system flags.
    """
    try:
        activities_repo.ensure_system_activities(user_id, DEFAULT_SYSTEM_ACTIVITIES)
    except SQLAlchemyError as exc:
        log_event(
            "activity.system_seed_failed",
            "Failed to seed system activities",
            user_id=user_id,
            level="error",
            context={"error": str(exc)},
        )
        raise
