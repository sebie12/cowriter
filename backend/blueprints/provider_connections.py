from flask import Blueprint, jsonify, request

if __package__ and __package__.startswith("backend."):
    from ..auth.connections import ProviderConnectionError
    from ..auth.providers.Ollama import OllamaProvider
    from ..database import ProviderConnection, db
else:
    from auth.connections import ProviderConnectionError
    from auth.providers.Ollama import OllamaProvider
    from database import ProviderConnection, db

provider_connections_bp = Blueprint(
    "provider_connections",
    __name__,
    url_prefix="/provider-connections",
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
    if connection.provider != "ollama":
        return jsonify({"error": "Model discovery is not implemented for this provider."}), 501
    if connection.status != "connected" or not connection.endpoint_url:
        return jsonify({"error": "Provider is not connected."}), 409

    try:
        models = OllamaProvider().list_models(connection.endpoint_url)
    except ProviderConnectionError as error:
        return jsonify({"error": error.message}), error.status_code

    return jsonify({
        "connection_id": connection.id,
        "provider": connection.provider,
        "models": [
            {"id": model, "name": model}
            for model in models
        ],
    })


@provider_connections_bp.route("/", methods=["POST"])
def create_provider_connection():
    payload = request.get_json(silent=True) or {}
    provider = payload.get("provider")
    auth_method_id = payload.get("auth_method_id")
    account_id = payload.get("account_id")
    account_label = payload.get("account_label")

    if not all(isinstance(field, str) and field.strip() for field in [provider, auth_method_id, account_id, account_label]):
        return jsonify({"error": "All fields are required"}), 400

    new_connection = ProviderConnection(
        provider=provider.strip(),
        auth_method_id=auth_method_id.strip(),
        account_id=account_id.strip(),
        account_label=account_label.strip(),
    )
    db.session.add(new_connection)
    db.session.commit()

    return jsonify(serialize_provider_connection(new_connection)), 201


@provider_connections_bp.route("/<int:connection_id>", methods=["DELETE"])
def delete_provider_connection(connection_id):
    conn = ProviderConnection.query.get_or_404(connection_id)
    db.session.delete(conn)
    db.session.commit()
    return jsonify({"message": "Provider connection deleted"}), 200
