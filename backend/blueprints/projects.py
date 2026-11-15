from flask import Blueprint, current_app, jsonify, request, url_for
from sqlalchemy.exc import IntegrityError

from backend.llm import LLMError
from backend.database import Conversation, Message, Project, Reference, db
from backend.prompts import SystemPrompts
from backend.services.project_service import ProjectService


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

    response = jsonify(project.to_dict())
    response.headers["Location"] = url_for("projects.get_project", project_id=project.id)
    return response, 201

@projects_bp.post("/<int:project_id>/open")
def open_project(project_id):
    project = ProjectService().project_opened(project_id)
    if not project:
        return jsonify({"error": "Project not found."}), 404

    return jsonify(project.to_dict()), 200


MAX_DRAFT_BYTES = 2_000_000


@projects_bp.put("/<int:project_id>/draft")
def save_draft(project_id):
    project = ProjectService().get_project_by_id(project_id)
    if not project:
        return jsonify({"error": "Project not found."}), 404

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict) or "draft" not in payload:
        return jsonify({"error": "draft is required."}), 400
    draft = payload["draft"]
    if draft is not None and (not isinstance(draft, dict) or draft.get("type") != "doc"):
        return jsonify({"error": "draft must be an editor document or null."}), 400
    if len(request.get_data()) > MAX_DRAFT_BYTES:
        return jsonify({"error": "draft is too large."}), 413

    project.draft = draft
    db.session.commit()
    return jsonify({"draft": project.draft, "updated_at": project.to_dict()["updated_at"]})


def _optional_string(payload, field_name, max_length):
    value = payload.get(field_name)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string or null.")
    value = value.strip()
    if len(value) > max_length:
        raise ValueError(f"{field_name} must be {max_length} characters or fewer.")
    return value or None


def _optional_int(payload, field_name):
    value = payload.get(field_name)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field_name} must be an integer or null.")
    return value


def parse_reference_payload(payload):
    if not isinstance(payload, dict):
        raise ValueError("Request body must be a JSON object.")
    paper_id = _optional_string(payload, "paper_id", 100)
    title = _optional_string(payload, "title", 1000)
    if not paper_id:
        raise ValueError("paper_id is required.")
    if not title:
        raise ValueError("title is required.")
    authors = payload.get("authors", [])
    if not isinstance(authors, list) or not all(isinstance(author, str) for author in authors):
        raise ValueError("authors must be an array of strings.")

    return {
        "paper_id": paper_id,
        "title": title,
        "year": _optional_int(payload, "year"),
        "authors": [author.strip() for author in authors if author.strip()][:200],
        "venue": _optional_string(payload, "venue", 500),
        "abstract": _optional_string(payload, "abstract", 20_000),
        "tldr": _optional_string(payload, "tldr", 5_000),
        "url": _optional_string(payload, "url", 2048),
        "pdf_url": _optional_string(payload, "pdf_url", 2048),
        "doi": _optional_string(payload, "doi", 255),
        "citation_count": _optional_int(payload, "citation_count"),
    }


@projects_bp.get("/<int:project_id>/references")
def list_references(project_id):
    project = ProjectService().get_project_by_id(project_id)
    if not project:
        return jsonify({"error": "Project not found."}), 404
    return jsonify([reference.to_dict() for reference in project.references])


@projects_bp.post("/<int:project_id>/references")
def save_reference(project_id):
    project = ProjectService().get_project_by_id(project_id)
    if not project:
        return jsonify({"error": "Project not found."}), 404
    try:
        values = parse_reference_payload(request.get_json(silent=True))
    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    existing = Reference.query.filter_by(project_id=project_id, paper_id=values["paper_id"]).first()
    if existing is not None:
        return jsonify({"error": "This paper is already saved.", "reference": existing.to_dict()}), 409

    reference = Reference(project_id=project_id, **values)
    db.session.add(reference)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "This paper is already saved."}), 409
    return jsonify(reference.to_dict()), 201


@projects_bp.delete("/<int:project_id>/references/<int:reference_id>")
def delete_reference(project_id, reference_id):
    reference = db.session.get(Reference, reference_id)
    if reference is None or reference.project_id != project_id:
        return jsonify({"error": "Reference not found."}), 404
    db.session.delete(reference)
    db.session.commit()
    return ("", 204)


@projects_bp.post("/<int:project_id>/proofread")
def proofread(project_id):
    project = ProjectService().get_project_by_id(project_id)
    if not project:
        return jsonify({"error": "Project not found."}), 404

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "Request body must be a JSON object."}), 400
    connection_id = payload.get("connection_id")
    provider = payload.get("provider")
    model = payload.get("model")
    text = payload.get("text")
    if isinstance(connection_id, bool) or not isinstance(connection_id, int) or connection_id < 1:
        return jsonify({"error": "connection_id is required."}), 400
    if not isinstance(provider, str) or not provider.strip():
        return jsonify({"error": "provider is required."}), 400
    if not isinstance(model, str) or not model.strip():
        return jsonify({"error": "model is required."}), 400
    if not isinstance(text, str):
        return jsonify({"error": "text is required."}), 400

    project_path = project.path.strip() if isinstance(project.path, str) and project.path.strip() else None
    try:
        issues = current_app.extensions["proofread_service"].review(
            connection_id=connection_id,
            provider=provider.strip(),
            model=model.strip(),
            text=text,
            description=project.description,
            references=[reference.to_dict() for reference in project.references],
            project_path=project_path,
        )
    except LLMError as error:
        return jsonify({"error": error.message}), error.status_code
    return jsonify({"issues": issues})
