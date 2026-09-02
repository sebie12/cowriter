import json

from flask import Blueprint, Response, current_app, jsonify, request, stream_with_context

if __package__ and __package__.startswith("backend."):
    from ..llm import ChatRequest, LLMError
    from ..prompts import SystemPrompts
else:
    from llm import ChatRequest, LLMError
    from prompts import SystemPrompts

chat_bp = Blueprint("chat", __name__, url_prefix="/api")
ALLOWED_HISTORY_ROLES = {"user", "assistant"}


def parse_chat_payload(payload):
    if not isinstance(payload, dict):
        raise LLMError("Request body must be a JSON object.")

    connection_id = payload.get("connection_id")
    provider = payload.get("provider")
    model = payload.get("model")
    message = payload.get("message")
    title = payload.get("title")
    description = payload.get("description")
    history = payload.get("history", [])

    if isinstance(connection_id, bool) or not isinstance(connection_id, int) or connection_id < 1:
        raise LLMError("connection_id is required.")
    if not isinstance(provider, str) or not provider.strip():
        raise LLMError("provider is required.")
    if not isinstance(model, str) or not model.strip():
        raise LLMError("model is required.")
    if not isinstance(message, str) or not message.strip():
        raise LLMError("message is required.")
    if title is not None and not isinstance(title, str):
        raise LLMError("title must be a string.")
    if description is not None and not isinstance(description, str):
        raise LLMError("description must be a string.")
    system_prompt = payload.get(
        "system_prompt",
        SystemPrompts.chat(
            title=title.strip() if title else None,
            description=description.strip() if description else None,
        ),
    )
    if system_prompt is not None and not isinstance(system_prompt, str):
        raise LLMError("system_prompt must be a string.")
    if not isinstance(history, list):
        raise LLMError("history must be an array.")

    normalized_history = []
    for history_message in history:
        if not isinstance(history_message, dict):
            raise LLMError("history contains an invalid message.")
        role = history_message.get("role")
        content = history_message.get("content")
        if role not in ALLOWED_HISTORY_ROLES or not isinstance(content, str) or not content.strip():
            raise LLMError("history contains an invalid message.")
        normalized_history.append({"role": role, "content": content.strip()})

    normalized_system_prompt = system_prompt.strip() if system_prompt else None
    return ChatRequest(
        connection_id=connection_id,
        provider=provider.strip(),
        model=model.strip(),
        message=message.strip(),
        system_prompt=normalized_system_prompt,
        history=tuple(normalized_history),
    )


@chat_bp.route("/chat", methods=["POST", "OPTIONS"])
def chat():
    if request.method == "OPTIONS":
        return ("", 204)

    try:
        chat_request = parse_chat_payload(request.get_json(silent=True))
        chunks = iter(current_app.extensions["chat_service"].stream_chat(chat_request))
        first_chunk = next(chunks)
    except StopIteration:
        return jsonify({"error": "The provider returned an empty response."}), 502
    except LLMError as error:
        return jsonify({"error": error.message}), error.status_code

    def generate():
        yield json.dumps({"type": "delta", "content": first_chunk}) + "\n"
        try:
            for chunk in chunks:
                yield json.dumps({"type": "delta", "content": chunk}) + "\n"
        except LLMError as error:
            yield json.dumps({"type": "error", "error": error.message}) + "\n"
            return
        yield json.dumps({"type": "done"}) + "\n"

    return Response(
        stream_with_context(generate()),
        mimetype="application/x-ndjson",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
