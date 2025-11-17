from flask import Blueprint, jsonify, request, send_file, Response

from controllers.helpers import current_user_id, is_admin_user, parse_pagination
from infra.cache_manager import invalidate_cache
from app import _set_export_headers, backup_manager
from security import jwt_required, ValidationError, error_response
from services import backup_service

backup_bp = Blueprint("backup", __name__)


@backup_bp.get("/backup/status")
@jwt_required()
def backup_status():
    try:
        status = backup_service.get_backup_status(backup_manager)
    except ValidationError as exc:
        return error_response(exc.code, exc.message, exc.status, exc.details)
    return jsonify(status)


@backup_bp.post("/backup/run")
@jwt_required()
def backup_run():
    operator_id = current_user_id()
    try:
        result, status = backup_service.run_backup(backup_manager, operator_id=operator_id)
    except ValidationError as exc:
        return error_response(exc.code, exc.message, exc.status, exc.details)
    return jsonify(result), status


@backup_bp.post("/backup/toggle")
@jwt_required()
def backup_toggle():
    operator_id = current_user_id()
    payload = request.get_json(silent=True) or {}
    try:
        result, status = backup_service.toggle_backup(backup_manager, operator_id=operator_id, payload=payload)
    except ValidationError as exc:
        return error_response(exc.code, exc.message, exc.status, exc.details)
    return jsonify(result), status


@backup_bp.get("/backup/download/<path:filename>")
@jwt_required()
def backup_download(filename: str):
    try:
        path = backup_service.resolve_backup_path(backup_manager, filename)
    except ValidationError as exc:
        return error_response(exc.code, exc.message, exc.status, exc.details)
    return send_file(path, as_attachment=True, download_name=path.name)


@backup_bp.get("/export/json")
@jwt_required()
def export_json():
    user_id = current_user_id()
    is_admin = is_admin_user()
    if user_id is None:
        return error_response("unauthorized", "Missing user context", 401)

    pagination = parse_pagination(default_limit=500, max_limit=2000)
    limit = pagination["limit"]
    offset = pagination["offset"]

    try:
        payload, meta = backup_service.build_export_payload(
            user_id=user_id,
            is_admin=is_admin,
            limit=limit,
            offset=offset,
        )
    except ValidationError as exc:
        return error_response(exc.code, exc.message, exc.status, exc.details)

    response = jsonify(payload)
    return _set_export_headers(
        response,
        "json",
        limit=limit,
        offset=offset,
        total_entries=meta["total_entries"],
        total_activities=meta["total_activities"],
    )


@backup_bp.get("/export/csv")
@jwt_required()
def export_csv():
    user_id = current_user_id()
    is_admin = is_admin_user()
    if user_id is None:
        return error_response("unauthorized", "Missing user context", 401)

    pagination = parse_pagination(default_limit=500, max_limit=2000)
    limit = pagination["limit"]
    offset = pagination["offset"]

    try:
        payload, meta = backup_service.build_export_payload(
            user_id=user_id,
            is_admin=is_admin,
            limit=limit,
            offset=offset,
        )
        csv_body = backup_service.build_export_csv(payload["entries"], payload["activities"])
    except ValidationError as exc:
        return error_response(exc.code, exc.message, exc.status, exc.details)

    response = Response(csv_body, mimetype="text/csv")
    return _set_export_headers(
        response,
        "csv",
        limit=limit,
        offset=offset,
        total_entries=meta["total_entries"],
        total_activities=meta["total_activities"],
    )
