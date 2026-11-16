import os
import sys
from pathlib import Path

from flask import Flask, jsonify, request
from flask_admin.contrib.sqla import ModelView

# Allow the documented `python backend/app.py` entry point to use package imports.
if __name__ == "__main__" and not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.admin_views import AuthMethodModelView, ProviderModelView
from backend.auth.credentials import CredentialStore
from backend.blueprints import (
    auth_methods_bp,
    chat_bp,
    projects_bp,
    provider_connections_bp,
    research_bp,
    providers_bp,
    tool_calls_bp,
)
from backend.database import admin, db, migrate
from backend.database.catalog import ensure_provider_catalog
from backend.database.models import (
    AuthMethod,
    Conversation,
    Message,
    Project,
    Provider,
    ProviderConnection,
    Reference,
    ToolCall,
)
from backend.services import (
    ChatService,
    ConversationService,
    ProofreadService,
    OpenAlexClient,
    ToolCallService,
)
from backend.services.chat_history import ChatHistoryService
from backend.services.project_settings import update_project_settings_tool

app = Flask(__name__)

app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY", "cowriter-dev-secret-key")
default_database_path = Path(__file__).resolve().parents[1] / "instance" / "database.db"
# SQLite creates the database file but not its parent directory.
default_database_path.parent.mkdir(parents=True, exist_ok=True)
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
    conversation_resolver=ConversationService().get_or_create_for_project,
    tool_call_service=ToolCallService(),
    local_tools=[update_project_settings_tool()],
    history_loader=lambda project_id: ChatHistoryService().timeline(project_id),
)
app.extensions["chat_history"] = ChatHistoryService()
app.extensions["proofread_service"] = ProofreadService(app.extensions["chat_service"])
app.extensions["research_client"] = OpenAlexClient()

# ===== BLUEPRINTS =====
app.register_blueprint(provider_connections_bp)
app.register_blueprint(providers_bp)
app.register_blueprint(auth_methods_bp)
app.register_blueprint(chat_bp)
app.register_blueprint(projects_bp)
app.register_blueprint(research_bp)
app.register_blueprint(tool_calls_bp)

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
        response.headers["Access-Control-Allow-Methods"] = "GET,POST,PUT,DELETE,OPTIONS"
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
admin.add_view(ModelView(ToolCall, db))
admin.add_view(ModelView(Reference, db))

if __name__ == "__main__":
    with app.app_context():
        ensure_provider_catalog(db)
    app.run(host="127.0.0.1", port=5000, debug=True)
