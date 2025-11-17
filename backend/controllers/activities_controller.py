import app as app_module
from flask import Blueprint

activities_bp = Blueprint("activities", __name__)


@activities_bp.get("/activities")
def get_activities():
    return app_module.get_activities()


@activities_bp.post("/add_activity")
def add_activity():
    return app_module.add_activity()


@activities_bp.put("/activities/<int:activity_id>")
def update_activity(activity_id):
    return app_module.update_activity(activity_id)


@activities_bp.patch("/activities/<int:activity_id>/deactivate")
def deactivate_activity(activity_id: int):
    return app_module.deactivate_activity(activity_id)


@activities_bp.patch("/activities/<int:activity_id>/activate")
def activate_activity(activity_id: int):
    return app_module.activate_activity(activity_id)


@activities_bp.delete("/activities/<int:activity_id>")
def delete_activity(activity_id: int):
    return app_module.delete_activity(activity_id)
