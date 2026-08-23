import os
from contextlib import nullcontext
from threading import Lock

from flask import Blueprint, current_app, jsonify, request

if __package__ and __package__.startswith("backend."):
    from ..auth.connections import ProviderAuthorizationResult, ProviderConnectionError, ProviderConnectionManager, normalize_auth_method, normalize_identifier
    from ..auth.credentials import CredentialStore
    from ..auth.oauth import google_oauth_manager
    from ..database import Provider, ProviderConnection, db
    from .provider_connections import serialize_provider_connection
else:
    from auth.connections import ProviderAuthorizationResult, ProviderConnectionError, ProviderConnectionManager, normalize_auth_method, normalize_identifier
    from auth.credentials import CredentialStore
    from auth.oauth import google_oauth_manager
    from database import Provider, ProviderConnection, db
    from blueprints.provider_connections import serialize_provider_connection

providers_bp = Blueprint(
    "providers",
    __name__,
    url_prefix="/api/providers",
)
credential_store = CredentialStore()
GOOGLE_PROVIDER_IDS = {"gemini", "google", "google_gemini"}
OLLAMA_CONNECTION_LOCK = Lock()


def find_provider(provider_id):
    return next(
        (
            candidate
            for candidate in Provider.query.all()
            if normalize_identifier(candidate.name) == provider_id
        ),
        None,
    )


def find_auth_method(provider, auth_method):
    return next(
        (
            candidate
            for candidate in provider.auth_methods
            if normalize_auth_method(candidate.method_name) == auth_method
        ),
        None,
    )


def save_provider_connection(result, auth_method_record):
    if result.credentials:
        credential_store.save(
            result.provider_id,
            result.account_id,
            result.credentials,
        )

    connection = ProviderConnection.query.filter_by(
        provider=result.provider_id,
        account_id=result.account_id,
    ).first()

    if connection is None:
        connection = ProviderConnection(
            provider=result.provider_id,
            account_id=result.account_id,
            account_label=result.account_label,
            endpoint_url=result.endpoint_url,
            auth_method_id=auth_method_record.id,
            status=result.status,
        )
        db.session.add(connection)
    else:
        connection.account_label = result.account_label
        connection.endpoint_url = result.endpoint_url
        connection.auth_method_id = auth_method_record.id
        connection.status = result.status

    db.session.commit()
    return connection

def serialize_provider(provider):
    return {
        "id": normalize_identifier(provider.name),
        "name": provider.name,
        "description": provider.description,
        "chat_supported": current_app.extensions["chat_service"].supports_provider(
            normalize_identifier(provider.name),
        ),
        "auth_methods": [
            method.method_name for method in provider.auth_methods
        ],
    }

@providers_bp.get("/")
def get_providers():
    providers = Provider.query.all()
    return jsonify([
        serialize_provider(provider)
        for provider in providers
    ])

@providers_bp.post("/<string:provider_name>/connect")
def connect_provider(provider_name):
    provider_id = normalize_identifier(provider_name)
    provider = find_provider(provider_id)

    if not provider:
        return jsonify({"error": "Provider not found"}), 404

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "Request body must be a JSON object."}), 400
    auth_method = payload.get("auth_method")

    if not isinstance(auth_method, str) or not auth_method.strip():
        return jsonify({"error": "auth_method is required"}), 400

    normalized_auth_method = normalize_auth_method(auth_method)
    auth_method_record = find_auth_method(provider, normalized_auth_method)

    if auth_method_record is None:
        return jsonify({"error": "Auth method is not supported by this provider."}), 400

    if normalized_auth_method == "oauth" and provider_id in GOOGLE_PROVIDER_IDS:
        project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
        if not project_id:
            return jsonify({
                "error": "Google Cloud project is not configured on the backend."
            }), 503

        payload["project_id"] = project_id
        payload["location"] = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
        payload["redirect_uri"] = os.environ.get(
            "GOOGLE_OAUTH_REDIRECT_URI",
            f"http://127.0.0.1:5000/api/providers/{provider_id}/oauth/callback",
        )

    connection_lock = OLLAMA_CONNECTION_LOCK if provider_id == "ollama" else nullcontext()
    with connection_lock:
        try:
            result = ProviderConnectionManager().connect(
                provider_id=provider_id,
                provider_name=provider.name,
                auth_method_name=auth_method,
                payload=payload,
            )
        except ProviderConnectionError as error:
            return jsonify({"error": error.message}), error.status_code

        if isinstance(result, ProviderAuthorizationResult):
            return jsonify({
                "provider": result.provider_id,
                "status": result.status,
                "attempt_id": result.attempt_id,
                "authorization_url": result.authorization_url,
            }), 202

        try:
            connection = save_provider_connection(result, auth_method_record)
        except Exception:
            db.session.rollback()
            return jsonify({"error": "Could not save provider connection."}), 500

        return jsonify(serialize_provider_connection(connection)), 201


@providers_bp.get("/<string:provider_name>/oauth/callback")
def oauth_callback(provider_name):
    provider_id = normalize_identifier(provider_name)
    state = request.args.get("state")
    if not state:
        return "Google OAuth request is missing state.", 400

    completed = None
    try:
        completed = google_oauth_manager.complete(
            state=state,
            authorization_response=request.url,
        )
        if completed.provider_id != provider_id:
            raise ProviderConnectionError("Google OAuth provider did not match.", 400)

        provider = find_provider(provider_id)
        if provider is None:
            raise ProviderConnectionError("Provider not found.", 404)
        auth_method_record = find_auth_method(provider, "oauth")
        if auth_method_record is None:
            raise ProviderConnectionError("OAuth is not supported by this provider.", 400)

        result = ProviderConnectionManager().connect(
            provider_id=provider_id,
            provider_name=provider.name,
            auth_method_name="oauth",
            payload={
                "credentials": completed.credentials,
                "project_id": completed.project_id,
                "location": completed.location,
                "account_id": completed.account_id,
                "account_label": completed.account_label,
            },
        )
        save_provider_connection(result, auth_method_record)
        google_oauth_manager.mark_connected(completed.attempt_id)
    except ProviderConnectionError as error:
        db.session.rollback()
        if completed is not None:
            google_oauth_manager.mark_error(completed.attempt_id, error.message)
        return f"Google OAuth failed: {error.message}", error.status_code
    except Exception:
        db.session.rollback()
        if completed is not None:
            google_oauth_manager.mark_error(
                completed.attempt_id,
                "Google OAuth failed while saving the connection.",
            )
        return "Google OAuth failed while saving the connection.", 500

    return (
        "<!doctype html><html><body style='font-family: sans-serif; padding: 2rem;'>"
        "<h1>Google connected</h1><p>You can close this window and return to Cowriter.</p>"
        "</body></html>"
    )


@providers_bp.get("/<string:provider_name>/oauth/status/<string:attempt_id>")
def oauth_status(provider_name, attempt_id):
    provider_id = normalize_identifier(provider_name)
    try:
        attempt = google_oauth_manager.get_attempt(
            provider_id=provider_id,
            attempt_id=attempt_id,
        )
    except ProviderConnectionError as error:
        return jsonify({"error": error.message}), error.status_code

    response = {
        "provider": attempt.provider_id,
        "status": attempt.status,
    }
    if attempt.error:
        response["error"] = attempt.error

    return jsonify(response)
