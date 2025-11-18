import structlog
from flask import Blueprint, Response, jsonify, request, stream_with_context
from security import ValidationError, error_response, jwt_required, limit_request
from services import nightmotion_service

nightmotion_bp = Blueprint("nightmotion", __name__)


@nightmotion_bp.route("/api/stream-proxy", methods=["GET"])
@jwt_required()
def stream_proxy():
    limited = limit_request("stream_proxy", per_minute=2)
    if limited:
        return limited

    rtsp_url = request.args.get("url", type=str)
    if not rtsp_url:
        return jsonify({"error": "Missing RTSP URL"}), 400

    cam_user = request.args.get("username", "", type=str) or ""
    cam_pass = request.args.get("password", "", type=str) or ""
    if cam_user and cam_pass and "@" not in rtsp_url:
        rtsp_url = rtsp_url.replace("rtsp://", f"rtsp://{cam_user}:{cam_pass}@", 1)

    logger = structlog.get_logger("mosaic.backend")
    logger.bind(stream="nightmotion", rtsp_url=rtsp_url).info("nightmotion.proxy_start")

    try:
        # Import lazily to avoid circular imports and enable tests to monkeypatch
        from app import stream_rtsp

        response = Response(
            stream_with_context(stream_rtsp(rtsp_url)),
            mimetype="multipart/x-mixed-replace; boundary=frame",
        )
        response.headers["Cache-Control"] = "no-store"
        return response
    except ValidationError as exc:
        return error_response(exc.code, exc.message, exc.status, exc.details)
    except PermissionError:
        return error_response("unauthorized", "Unauthorized", 401)
    except RuntimeError as exc:
        logger.bind(stream="nightmotion").exception(
            "nightmotion.stream_error", error=str(exc)
        )
        return error_response("internal_error", "Stream nelze navázat", 500)
    except Exception as exc:
        logger.bind(stream="nightmotion").exception(
            "nightmotion.stream_error_unexpected", error=str(exc)
        )
        return error_response("internal_error", "Stream nelze navázat", 500)
