import app as app_module
from flask import Blueprint

wearable_bp = Blueprint("wearable", __name__)


@wearable_bp.post("/ingest/wearable/batch")
def ingest_wearable_batch():
    return app_module.ingest_wearable_batch()
