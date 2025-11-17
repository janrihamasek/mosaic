import app as app_module
from flask import Blueprint
from security import jwt_required

backup_bp = Blueprint("backup", __name__)


@backup_bp.get("/backup/status")
@jwt_required()
def backup_status():
    return app_module.backup_status()


@backup_bp.post("/backup/run")
@jwt_required()
def backup_run():
    return app_module.backup_run()


@backup_bp.post("/backup/toggle")
@jwt_required()
def backup_toggle():
    return app_module.backup_toggle()


@backup_bp.get("/backup/download/<path:filename>")
@jwt_required()
def backup_download(filename: str):
    return app_module.backup_download(filename)


@backup_bp.get("/export/json")
@jwt_required()
def export_json():
    return app_module.export_json()


@backup_bp.get("/export/csv")
@jwt_required()
def export_csv():
    return app_module.export_csv()
