from flask import Blueprint, jsonify, request
from sqlalchemy.exc import IntegrityError

if __package__ and __package__.startswith("backend."):
    from ..database import Conversation, Message, Project, db
    from ..prompts import SystemPrompts
    from ..services.project_service import ProjectService
else:
    from database import Conversation, Message, Project, db
    from prompts import SystemPrompts
    from services.project_service import ProjectService


projects_bp = Blueprint(
    "projects",
    __name__,
    url_prefix="/api/projects",
)
ALLOWED_MESSAGE_ROLES = {"system", "user", "assistant"}
DESCRIPTION_OPTIONS = {
    "tone": {"Academic", "Neutral", "Persuasive", "Analytical", "Conversational"},
    "writing_style": {"Formal", "Clear", "Concise", "Descriptive", "Creative"},
    "academic_level": {"MiddleSchool", "HighSchool", "Undergraduate", "Graduate"},
    "language": {"Portuguese", "English"},
    "essay_type": {"Argumentative", "Expository", "Descriptive", "Narrative", "Analytical"},
}
MAX_ADDITIONAL_INSTRUCTIONS_LENGTH = 110


def parse_project_description(description):
    if description is None:
        return None
    if not isinstance(description, dict):
        raise ValueError("description must be an object or null.")

    values = {}
    for field_name, allowed_values in DESCRIPTION_OPTIONS.items():
        value = description.get(field_name)
        if value not in allowed_values:
            raise ValueError(f"description.{field_name} is invalid.")
        values[field_name] = value

    additional_instructions = description.get("additional_instructions")
    if additional_instructions is not None and not isinstance(additional_instructions, str):
        raise ValueError("description.additional_instructions must be a string or null.")
    if isinstance(additional_instructions, str):
        additional_instructions = additional_instructions.strip() or None
        if (
            additional_instructions
            and len(additional_instructions) > MAX_ADDITIONAL_INSTRUCTIONS_LENGTH
        ):
            raise ValueError(
                f"description.additional_instructions must be {MAX_ADDITIONAL_INSTRUCTIONS_LENGTH} characters or fewer."
            )

    project_description = SystemPrompts.project_description(
        tone=values["tone"],
        writing_style=values["writing_style"],
        academic_level=values["academic_level"],
        language=values["language"],
        essay_type=values["essay_type"],
        additional_instructions=additional_instructions,
    )
    if len(project_description) > 255:
        raise ValueError("description must be 255 characters or fewer.")
    return project_description


def parse_project_payload(payload):
    if not isinstance(payload, dict):
        raise ValueError("Request body must be a JSON object.")

    name = payload.get("name")
    description = payload.get("description")
    conversation_payloads = payload.get("conversations", [])
    path = payload.get("path")

    if not isinstance(name, str) or not name.strip():
        raise ValueError("name is required.")
    name = name.strip()
    if len(name) > 100:
        raise ValueError("name must be 100 characters or fewer.")

    description = parse_project_description(description)

    if path is not None and not isinstance(path, str):
        raise ValueError("path must be a string or null.")
    if isinstance(path, str):
        path = path.strip() or None
        if path and len(path) > 255:
            raise ValueError("path must be 255 characters or fewer.")
    if path is not None and Project.query.filter_by(path=path).first() is not None:
        raise ValueError("A project with this path already exists.")

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
        path=path,
        conversations=conversations,
    )

@projects_bp.route("", methods=["GET"], strict_slashes=False)
def get_projects():
    projects = ProjectService().get_all_projects()
    return jsonify([project.to_dict() for project in projects])


@projects_bp.route("/<int:project_id>", methods=["GET"], strict_slashes=False)
def get_project(project_id):
    project = ProjectService().get_project_by_id(project_id)
    if not project:
        return jsonify({"error": "Project not found."}), 404
    return jsonify(project.to_dict())


@projects_bp.route("/<int:project_id>", methods=["DELETE"], strict_slashes=False)
def delete_project(project_id):
    project = ProjectService().get_project_by_id(project_id)
    if not project:
        return jsonify({"error": "Project not found."}), 404

    ProjectService().delete_project(project_id)
    return jsonify({"message": "Project deleted successfully."}), 200

@projects_bp.route("", methods=["POST"], strict_slashes=False)
def create_project():
    try:
        project = parse_project_payload(request.get_json(silent=True))
    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    try:
        ProjectService().create_project(project)
    except IntegrityError:
        return jsonify({"error": "A project with this name or path already exists."}), 409

    return jsonify(project.to_dict()), 201

@projects_bp.route("/<int:project_id>", methods=["PATCH"], strict_slashes=False)
def update_project(project_id):
    project = ProjectService().project_opened(project_id)
    if not project:
        return jsonify({"error": "Project not found."}), 404

    return jsonify(project.to_dict()), 200
