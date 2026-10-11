from flask import Blueprint, current_app, jsonify

from backend.database import ProviderConnection, db
from backend.llm import LLMError

provider_connections_bp = Blueprint(
    "provider_connections",
    __name__,
    url_prefix="/api/provider-connections",
)

def serialize_provider_connection(conn):
    return {
        "id": conn.id,
        "provider": conn.provider,
        "auth_method": conn.auth_method.method_name if conn.auth_method else None,
        "auth_method_id": conn.auth_method_id,
        "account_id": conn.account_id,
        "account_label": conn.account_label,
        "endpoint_url": conn.endpoint_url,
        "status": conn.status,
        "expires_at": conn.expires_at.isoformat() if conn.expires_at else None,
        "created_at": conn.created_at.isoformat() if conn.created_at else None,
        "updated_at": conn.updated_at.isoformat() if conn.updated_at else None,
    }


@provider_connections_bp.route("/", methods=["GET"])
def get_provider_connections():
    connections = ProviderConnection.query.all()
    return jsonify([serialize_provider_connection(conn) for conn in connections])


@provider_connections_bp.route("/<int:connection_id>", methods=["GET"])
def get_provider_connection(connection_id):
    conn = ProviderConnection.query.get_or_404(connection_id)
    return jsonify(serialize_provider_connection(conn))


@provider_connections_bp.get("/<int:connection_id>/models")
def get_provider_connection_models(connection_id):
    connection = db.session.get(ProviderConnection, connection_id)
    if connection is None:
        return jsonify({"error": "Provider connection not found."}), 404
    try:
        provider_id, models = current_app.extensions["chat_service"].list_models(connection_id)
    except LLMError as error:
        return jsonify({"error": error.message}), error.status_code

    return jsonify({
        "connection_id": connection.id,
        "provider": provider_id,
        "models": [
            {"id": model, "name": model}
            for model in models
        ],
    })


@provider_connections_bp.route("/<int:connection_id>", methods=["DELETE"])
def delete_provider_connection(connection_id):
    conn = ProviderConnection.query.get_or_404(connection_id)
    db.session.delete(conn)
    db.session.commit()
    return jsonify({"message": "Provider connection deleted"}), 200
