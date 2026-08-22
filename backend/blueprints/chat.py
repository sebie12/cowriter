from flask import Blueprint, jsonify, request

if __package__ and __package__.startswith("backend."):
    from ..auth.connections import ProviderConnectionError
    from ..auth.providers.Ollama import OllamaProvider
    from ..database import ProviderConnection, db
else:
    from auth.connections import ProviderConnectionError
    from auth.providers.Ollama import OllamaProvider
    from database import ProviderConnection, db

chat_bp = Blueprint("chat", __name__, url_prefix="/api")
ALLOWED_MESSAGE_ROLES = {"system", "user", "assistant"}


def parse_chat_payload(payload):
    if not isinstance(payload, dict):
        raise ProviderConnectionError("Request body must be a JSON object.")

    connection_id = payload.get("connection_id")
    model = payload.get("model")
    messages = payload.get("messages")

    if isinstance(connection_id, bool) or not isinstance(connection_id, int) or connection_id < 1:
        raise ProviderConnectionError("connection_id is required.")
    if not isinstance(model, str) or not model.strip():
        raise ProviderConnectionError("model is required.")
    if not isinstance(messages, list) or not messages:
        raise ProviderConnectionError("messages are required.")

    normalized_messages = []
    for message in messages:
        if not isinstance(message, dict):
            raise ProviderConnectionError("messages contains an invalid message.")
        role = message.get("role")
        content = message.get("content")
        if role not in ALLOWED_MESSAGE_ROLES or not isinstance(content, str) or not content.strip():
            raise ProviderConnectionError("messages contains an invalid message.")
        normalized_messages.append({"role": role, "content": content.strip()})

    return connection_id, model.strip(), normalized_messages


@chat_bp.route("/chat", methods=["POST", "OPTIONS"])
def chat():
    if request.method == "OPTIONS":
        return ("", 204)

    try:
        connection_id, model, messages = parse_chat_payload(request.get_json(silent=True))
    except ProviderConnectionError as error:
        return jsonify({"error": error.message}), error.status_code

    connection = db.session.get(ProviderConnection, connection_id)
    if connection is None:
        return jsonify({"error": "Provider connection not found."}), 404
    if connection.provider != "ollama":
        return jsonify({"error": "Chat is not implemented for this provider."}), 501
    if connection.status != "connected" or not connection.endpoint_url:
        return jsonify({"error": "Provider is not connected."}), 409

    try:
        content = OllamaProvider().chat(
            endpoint_url=connection.endpoint_url,
            model=model,
            messages=messages,
        )
    except ProviderConnectionError as error:
        return jsonify({"error": error.message}), error.status_code

    return jsonify({"message": content})
