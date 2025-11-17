import app as app_module
from flask import Blueprint

stats_bp = Blueprint("stats", __name__)


@stats_bp.get("/stats/progress")
def get_progress_stats():
    return app_module.get_progress_stats()
