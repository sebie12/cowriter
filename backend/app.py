import os

from flask import Flask, jsonify, request

if __package__:
    from .admin_views import AuthMethodModelView, ProviderModelView
    from .blueprints import auth_methods_bp, chat_bp, provider_connections_bp, providers_bp
    from .database import db, admin
    from .database.catalog import ensure_ollama_catalog
    from .database.migrations import ensure_provider_connection_indexes, migrate_provider_connections_schema
    from .database.models import AuthMethod, Provider, ProviderConnection
else:
    try:
        from admin_views import AuthMethodModelView, ProviderModelView
    except ImportError:
        from backend.admin_views import AuthMethodModelView, ProviderModelView

    from blueprints import auth_methods_bp, chat_bp, provider_connections_bp, providers_bp
    from database import db, admin
    from database.catalog import ensure_ollama_catalog
    from database.migrations import ensure_provider_connection_indexes, migrate_provider_connections_schema
    from database.models import AuthMethod, Provider, ProviderConnection

from flask_admin.contrib.sqla import ModelView
from sqlalchemy import text

app = Flask(__name__)

app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY", "cowriter-dev-secret-key")
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = True

db.init_app(app)
admin.init_app(app)

# ===== BLUEPRINTS =====
app.register_blueprint(provider_connections_bp)
app.register_blueprint(providers_bp)
app.register_blueprint(auth_methods_bp)
app.register_blueprint(chat_bp)

with app.app_context():
    db.create_all()
    migrate_provider_connections_schema(db)
    ensure_provider_connection_indexes(db)
    ensure_ollama_catalog(db)
    db.session.execute(
        text(
            "CREATE UNIQUE INDEX IF NOT EXISTS "
            "ix_auth_methods_method_name ON auth_methods (method_name)"
        )
    )
    db.session.commit()

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
        response.headers["Access-Control-Allow-Methods"] = "GET,POST,DELETE,OPTIONS"
        response.headers.add("Vary", "Origin")
    return response


@app.get("/api/health")
def health():
    return jsonify({"status": "ok"})


admin.add_view(ProviderModelView(Provider, db))
admin.add_view(AuthMethodModelView(AuthMethod, db))
admin.add_view(ModelView(ProviderConnection, db))

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
