import app as app_module
from flask import Blueprint
from security import jwt_required

nightmotion_bp = Blueprint("nightmotion", __name__)


@nightmotion_bp.route("/api/stream-proxy", methods=["GET"])
@jwt_required()
def stream_proxy():
    return app_module.stream_proxy()
