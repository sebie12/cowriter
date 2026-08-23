from flask import Blueprint, jsonify, request
from sqlalchemy.exc import IntegrityError

if __package__ and __package__.startswith("backend."):
    from ..database import Conversation, Essay, Message, Project, db
else:
    from database import Conversation, Essay, Message, Project, db


projects_bp = Blueprint(
    "projects",
    __name__,
    url_prefix="/api/projects",
)
ALLOWED_MESSAGE_ROLES = {"system", "user", "assistant"}


def parse_project_payload(payload):
    if not isinstance(payload, dict):
        raise ValueError("Request body must be a JSON object.")

    name = payload.get("name")
    description = payload.get("description")
    essay_payload = payload.get("essay")
    conversation_payloads = payload.get("conversations", [])

    if not isinstance(name, str) or not name.strip():
        raise ValueError("name is required.")
    name = name.strip()
    if len(name) > 100:
        raise ValueError("name must be 100 characters or fewer.")

    if description is not None and not isinstance(description, str):
        raise ValueError("description must be a string or null.")
    if isinstance(description, str):
        description = description.strip() or None
        if description and len(description) > 255:
            raise ValueError("description must be 255 characters or fewer.")

    if not isinstance(essay_payload, dict):
        raise ValueError("essay is required.")
    essay_title = essay_payload.get("title")
    if not isinstance(essay_title, str) or not essay_title.strip():
        raise ValueError("essay.title is required.")
    essay_title = essay_title.strip()
    if len(essay_title) > 200:
        raise ValueError("essay.title must be 200 characters or fewer.")

    if not isinstance(conversation_payloads, list):
        raise ValueError("conversations must be an array.")

    conversations = []
    for conversation_payload in conversation_payloads:
        if not isinstance(conversation_payload, dict):
            raise ValueError("conversations contains an invalid conversation.")

        message_payloads = conversation_payload.get("messages", [])
        if not isinstance(message_payloads, list):
            raise ValueError("conversation.messages must be an array.")

        messages = []
        for message_payload in message_payloads:
            if not isinstance(message_payload, dict):
                raise ValueError("conversation.messages contains an invalid message.")
            role = message_payload.get("role")
            content = message_payload.get("content")
            if role not in ALLOWED_MESSAGE_ROLES:
                raise ValueError("message.role must be system, user, or assistant.")
            if not isinstance(content, str) or not content.strip():
                raise ValueError("message.content is required.")
            messages.append(Message(role=role, content=content.strip()))

        conversations.append(Conversation(messages=messages))

    return Project(
        name=name,
        description=description,
        essay=Essay(title=essay_title),
        conversations=conversations,
    )


@projects_bp.route("", methods=["GET"], strict_slashes=False)
def get_projects():
    projects = Project.query.order_by(Project.updated_at.desc(), Project.id.desc()).all()
    return jsonify([project.to_dict() for project in projects])


@projects_bp.route("", methods=["POST"], strict_slashes=False)
def create_project():
    try:
        project = parse_project_payload(request.get_json(silent=True))
    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    try:
        db.session.add(project)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "A project with this name already exists."}), 409

    return jsonify(project.to_dict()), 201
