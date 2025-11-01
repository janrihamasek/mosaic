from flask_migrate import Migrate  # type: ignore[import]
from flask_sqlalchemy import SQLAlchemy  # type: ignore[import]

db = SQLAlchemy()
migrate = Migrate()
