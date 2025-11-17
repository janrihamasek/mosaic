import app as app_module
from flask import Blueprint

entries_bp = Blueprint("entries", __name__)


@entries_bp.get("/entries")
def get_entries():
    return app_module.get_entries()


@entries_bp.post("/add_entry")
def add_entry():
    return app_module.add_entry()


@entries_bp.delete("/entries/<int:entry_id>")
def delete_entry(entry_id):
    return app_module.delete_entry(entry_id)


@entries_bp.get("/today")
def get_today():
    return app_module.get_today()


@entries_bp.post("/finalize_day")
def finalize_day():
    return app_module.finalize_day()


@entries_bp.post("/import_csv")
def import_csv_endpoint():
    return app_module.import_csv_endpoint()
