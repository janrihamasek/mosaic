import os
import tempfile
from typing import Any, Dict

from audit import log_event
from controllers.helpers import current_user_id, is_admin_user, parse_pagination
from flask import Blueprint, current_app, g, jsonify, request
from import_data import import_csv as run_import_csv
from infra.cache_manager import TODAY_CACHE_TTL, cache_get, cache_set, invalidate_cache
from security import (
    ValidationError,
    error_response,
    rate_limit,
    validate_csv_import_payload,
)
from services import entries_service
from werkzeug.utils import secure_filename

entries_bp = Blueprint("entries", __name__)


@entries_bp.get("/entries")
def get_entries():
    user_id = current_user_id()
    is_admin = is_admin_user()
    if user_id is None:
        return error_response("unauthorized", "Missing user context", 401)

    start_date = (request.args.get("start_date") or "").strip() or None
    end_date = (request.args.get("end_date") or "").strip() or None
    activity_filter_raw = request.args.get("activity") or ""
    category_filter_raw = request.args.get("category") or ""

    def normalize_filter(value, all_markers):
        candidate = value.strip()
        if not candidate:
            return None
        if candidate.lower() in all_markers:
            return None
        return candidate

    activity_filter = normalize_filter(
        activity_filter_raw, {"all", "all activities", "all_activities"}
    )
    category_filter = normalize_filter(
        category_filter_raw, {"all", "all categories", "all_categories"}
    )

    try:
        pagination = parse_pagination()
        entries = entries_service.list_entries(
            user_id=user_id,
            is_admin=is_admin,
            start_date=start_date,
            end_date=end_date,
            activity_filter=activity_filter,
            category_filter=category_filter,
            limit=pagination["limit"],
            offset=pagination["offset"],
        )
    except ValidationError as exc:
        return error_response(exc.code, exc.message, exc.status, exc.details)

    return jsonify(entries)


@entries_bp.post("/add_entry")
def add_entry():
    user_id = current_user_id()
    if user_id is None:
        return error_response("unauthorized", "Missing user context", 401)

    limits = current_app.config["RATE_LIMITS"]["add_entry"]
    limited = rate_limit("add_entry", limits["limit"], limits["window"])
    if limited:
        return limited

    idempotency_key = request.headers.get("X-Idempotency-Key")
    data: Dict[str, Any] = request.get_json() or {}

    try:
        result, status = entries_service.add_entry(
            user_id=user_id,
            payload=data,
            idempotency_key=idempotency_key,
            invalidate_cache_cb=invalidate_cache,
        )
    except ValidationError as exc:
        return error_response(exc.code, exc.message, exc.status, exc.details)

    return jsonify(result), status


@entries_bp.delete("/entries/<int:entry_id>")
def delete_entry(entry_id):
    user = getattr(g, "current_user", None)
    user_id = user["id"] if user else None
    is_admin = bool(user["is_admin"]) if user else False
    if user_id is None:
        return error_response("unauthorized", "Missing user context", 401)

    limits = current_app.config["RATE_LIMITS"]["delete_entry"]
    limited = rate_limit("delete_entry", limits["limit"], limits["window"])
    if limited:
        return limited

    try:
        result, status = entries_service.delete_entry(
            entry_id,
            user_id=user_id,
            is_admin=is_admin,
            invalidate_cache_cb=invalidate_cache,
        )
    except ValidationError as exc:
        return error_response(exc.code, exc.message, exc.status, exc.details)
    return jsonify(result), status


@entries_bp.get("/today")
def get_today():
    user = getattr(g, "current_user", None)
    user_id = user["id"] if user else None
    is_admin = bool(user["is_admin"]) if user else False
    if user_id is None:
        return error_response("unauthorized", "Missing user context", 401)

    date = (request.args.get("date") or "").strip() or None
    try:
        from services import stats_service  # local import to avoid circulars

        data = stats_service.get_today_payload(
            user_id=user_id,
            is_admin=is_admin,
            date=date,
            cache_get=cache_get,
            cache_set=cache_set,
            today_cache_ttl=TODAY_CACHE_TTL,
        )
    except ValidationError as exc:
        return error_response(exc.code, exc.message, exc.status, exc.details)

    return jsonify(data)


@entries_bp.post("/finalize_day")
def finalize_day():
    user = getattr(g, "current_user", None)
    user_id = user["id"] if user else None
    is_admin = bool(user["is_admin"]) if user else False
    if user_id is None:
        return error_response("unauthorized", "Missing user context", 401)

    limits = current_app.config["RATE_LIMITS"]["finalize_day"]
    limited = rate_limit("finalize_day", limits["limit"], limits["window"])
    if limited:
        return limited

    data: Dict[str, Any] = request.get_json() or {}
    try:
        result, status = entries_service.finalize_day(
            user_id=user_id,
            is_admin=is_admin,
            payload=data,
            invalidate_cache_cb=invalidate_cache,
        )
    except ValidationError as exc:
        return error_response(exc.code, exc.message, exc.status, exc.details)
    return jsonify(result), status


@entries_bp.post("/import_csv")
def import_csv_endpoint():
    user_id = current_user_id()
    if user_id is None:
        return error_response("unauthorized", "Missing user context", 401)
    limits = current_app.config["RATE_LIMITS"]["import_csv"]
    limited = rate_limit("import_csv", limits["limit"], limits["window"])
    if limited:
        return limited

    file = validate_csv_import_payload(request.files)
    filename_input = file.filename or "import.csv"
    filename = secure_filename(filename_input)
    suffix = os.path.splitext(filename)[1] or ".csv"
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            file.save(tmp.name)
            tmp_path = tmp.name
        summary = run_import_csv(tmp_path, user_id=user_id)
    except Exception as exc:  # pragma: no cover - defensive
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)
        log_event(
            "import.csv_failed",
            "CSV import failed",
            user_id=user_id,
            level="error",
            context={"error": str(exc), "filename": filename},
        )
        return error_response("import_failed", f"Failed to import CSV: {exc}", 500)
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)

    invalidate_cache("today")
    invalidate_cache("stats")
    log_event(
        "import.csv",
        "CSV import completed",
        user_id=user_id,
        context={"summary": summary, "filename": filename},
    )
    return jsonify({"message": "CSV import completed", "summary": summary}), 200
