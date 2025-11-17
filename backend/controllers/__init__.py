from .activities_controller import activities_bp
from .admin_controller import admin_bp
from .auth_controller import auth_bp
from .backup_controller import backup_bp
from .entries_controller import entries_bp
from .nightmotion_controller import nightmotion_bp
from .stats_controller import stats_bp
from .wearable_controller import wearable_bp


def register_controllers(app):
    app.register_blueprint(admin_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(activities_bp)
    app.register_blueprint(entries_bp)
    app.register_blueprint(stats_bp)
    app.register_blueprint(backup_bp)
    app.register_blueprint(nightmotion_bp)
    app.register_blueprint(wearable_bp)
