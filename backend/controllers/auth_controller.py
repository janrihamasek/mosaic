import app as app_module
from flask import Blueprint
from security import jwt_required

auth_bp = Blueprint("auth", __name__)


@auth_bp.post("/register")
def register():
    return app_module.register()


@auth_bp.post("/login")
def login():
    return app_module.login()


@auth_bp.get("/user")
@jwt_required()
def get_current_user():
    return app_module.get_current_user_profile()


@auth_bp.patch("/user")
@jwt_required()
def update_current_user():
    return app_module.update_current_user()


@auth_bp.delete("/user")
@jwt_required()
def delete_current_user():
    return app_module.delete_current_user()
