import os
from pathlib import Path

from flask import Flask, jsonify, request

if __package__:
    from .admin_views import AuthMethodModelView, ProviderModelView
    from .blueprints import (
        auth_methods_bp,
        chat_bp,
        projects_bp,
        provider_connections_bp,
        providers_bp,
    )
    from .database import admin, db, migrate
    from .database.catalog import ensure_provider_catalog
    from .database.models import (
        AuthMethod,
        Conversation,
        Message,
        Project,
        Provider,
        ProviderConnection,
    )
    from .services import ChatService
    from .auth.credentials import CredentialStore
else:
    try:
        from admin_views import AuthMethodModelView, ProviderModelView
    except ImportError:
        from backend.admin_views import AuthMethodModelView, ProviderModelView

    from blueprints import (
        auth_methods_bp,
        chat_bp,
        projects_bp,
        provider_connections_bp,
        providers_bp,
    )
    from database import admin, db, migrate
    from database.catalog import ensure_provider_catalog
    from database.models import (
        AuthMethod,
        Conversation,
        Message,
        Project,
        Provider,
        ProviderConnection,
    )
    from services import ChatService
    from auth.credentials import CredentialStore

from flask_admin.contrib.sqla import ModelView

app = Flask(__name__)

app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY", "cowriter-dev-secret-key")
default_database_path = Path(__file__).resolve().parents[1] / "instance" / "database.db"
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "COWRITER_DATABASE_URI",
    f"sqlite:///{default_database_path}",
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = True

db.init_app(app)
admin.init_app(app)
migrate.init_app(app, db, compare_type=True, render_as_batch=True)
app.extensions["chat_service"] = ChatService(
    connection_lookup=lambda connection_id: db.session.get(ProviderConnection, connection_id),
    credential_store=CredentialStore(),
    project_lookup=lambda project_id: db.session.get(Project, project_id),
)

# ===== BLUEPRINTS =====
app.register_blueprint(provider_connections_bp)
app.register_blueprint(providers_bp)
app.register_blueprint(auth_methods_bp)
app.register_blueprint(chat_bp)
app.register_blueprint(projects_bp)

DEFAULT_ALLOWED_ORIGINS = {
    "http://127.0.0.1:5173",
    "http://localhost:5173",
    "http://tauri.localhost",
    "https://tauri.localhost",
    "tauri://localhost",
}
configured_origins = {
    origin.strip()
    for origin in os.environ.get("COWRITER_ALLOWED_ORIGINS", "").split(",")
    if origin.strip()
}
allowed_origins = DEFAULT_ALLOWED_ORIGINS | configured_origins

@app.after_request
def add_cors_headers(response):
    origin = request.headers.get("Origin")
    if origin in allowed_origins:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        response.headers["Access-Control-Allow-Methods"] = "GET,POST,PATCH,DELETE,OPTIONS"
        response.headers.add("Vary", "Origin")
    return response


@app.get("/api/health")
def health():
    return jsonify({"status": "ok"})


admin.add_view(ProviderModelView(Provider, db))
admin.add_view(AuthMethodModelView(AuthMethod, db))
admin.add_view(ModelView(ProviderConnection, db))
admin.add_view(ModelView(Project, db))
admin.add_view(ModelView(Conversation, db))
admin.add_view(ModelView(Message, db))

if __name__ == "__main__":
    with app.app_context():
        ensure_provider_catalog(db)
    app.run(host="127.0.0.1", port=5000, debug=True)
