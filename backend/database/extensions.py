import sqlite3
from pathlib import Path

from flask_sqlalchemy import SQLAlchemy
from flask_admin import Admin
from flask_migrate import Migrate
from sqlalchemy import event
from sqlalchemy.engine import Engine


@event.listens_for(Engine, "connect")
def enable_sqlite_foreign_keys(dbapi_connection, _connection_record):
    if isinstance(dbapi_connection, sqlite3.Connection):
        dbapi_connection.execute("PRAGMA foreign_keys=ON")


db = SQLAlchemy()
admin = Admin(name="Admin")
migrate = Migrate(
    directory=str(Path(__file__).resolve().parents[1] / "migrations")
)
