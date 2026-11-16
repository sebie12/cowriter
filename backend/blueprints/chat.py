import json
from typing import Any

from flask import Blueprint, Response, current_app, jsonify, request, stream_with_context

from backend.llm import ChatRequest, LLMError
from backend.prompts import SystemPrompts
from backend.services.chat_history import utc_from_iso

chat_bp = Blueprint("chat", __name__, url_prefix="/api")
ALLOWED_HISTORY_ROLES = {"user", "assistant"}


def parse_chat_payload(payload):
    if not isinstance(payload, dict):
        raise LLMError("Request body must be a JSON object.")

    connection_id = payload.get("connection_id")
    provider = payload.get("provider")
    model = payload.get("model")
    message = payload.get("message")
    project_id = payload.get("project_id")
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
    if project_id is not None and (
        isinstance(project_id, bool) or not isinstance(project_id, int) or project_id < 1
    ):
        raise LLMError("project_id must be a positive integer.")
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
        project_id=project_id,
    )


class AssistantMessageRecorder:
    """Collects streamed assistant segments and saves each one to the project's chat."""

    def __init__(self, history: Any | None, project_id: int | None):
        self.history = history if project_id is not None else None
        self.project_id = project_id
        self.pending: dict[str, tuple[Any, list[str]]] = {}

    def observe(self, event: dict[str, Any]) -> None:
        if self.history is None:
            return
        event_type = event.get("type")
        message_id = event.get("id")
        if event_type == "assistant_start":
            self.pending[message_id] = (utc_from_iso(event.get("created_at")), [])
        elif event_type == "assistant_delta" and message_id in self.pending:
            self.pending[message_id][1].append(event.get("content") or "")
        elif event_type == "assistant_end":
            self._save(message_id)

    def flush(self) -> None:
        """Save segments cut short by an error or a stopped response."""
        for message_id in list(self.pending):
            try:
                self._save(message_id)
            except Exception:
                current_app.logger.exception("Could not save a partial assistant message.")

    def _save(self, message_id: str) -> None:
        created_at, parts = self.pending.pop(message_id, (None, []))
        content = "".join(parts).strip()
        if content:
            self.history.add_message(self.project_id, "assistant", content, created_at)


@chat_bp.route("/chat", methods=["POST", "OPTIONS"])
def chat():
    if request.method == "OPTIONS":
        return ("", 204)

    history = current_app.extensions.get("chat_history")
    try:
        chat_request = parse_chat_payload(request.get_json(silent=True))
        sent_at = utc_from_iso(None)
        events = iter(current_app.extensions["chat_service"].stream_chat(chat_request))
        first_event = next(events)
    except StopIteration:
        return jsonify({"error": "The provider returned an empty response."}), 502
    except LLMError as error:
        return jsonify({"error": error.message}), error.status_code

    # Saved only once the chat has started, so a rejected request leaves no history behind.
    if history is not None and chat_request.project_id is not None:
        history.add_message(chat_request.project_id, "user", chat_request.message, sent_at)
    recorder = AssistantMessageRecorder(history, chat_request.project_id)

    def generate():
        try:
            recorder.observe(first_event)
            yield json.dumps(first_event) + "\n"
            try:
                for event in events:
                    recorder.observe(event)
                    yield json.dumps(event) + "\n"
            except LLMError as error:
                yield json.dumps({"type": "error", "error": error.message}) + "\n"
                return
            yield json.dumps({"type": "done"}) + "\n"
        finally:
            recorder.flush()

    return Response(
        stream_with_context(generate()),
        mimetype="application/x-ndjson",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
