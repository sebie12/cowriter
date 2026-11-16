"""A project's writing settings: validation, the prose description built from them, and updates."""

from typing import Any

from sqlalchemy.exc import IntegrityError

from backend.database import Project, db
from backend.llm.contracts import ToolDefinition
from backend.prompts import SystemPrompts
from backend.services.chat_service import LocalTool


SETTING_OPTIONS = {
    "tone": ("Academic", "Neutral", "Persuasive", "Analytical", "Conversational"),
    "writing_style": ("Formal", "Clear", "Concise", "Descriptive", "Creative"),
    "academic_level": ("MiddleSchool", "HighSchool", "Undergraduate", "Graduate"),
    "language": ("Portuguese", "English"),
    "essay_type": ("Argumentative", "Expository", "Descriptive", "Narrative", "Analytical"),
}
# Mirrors DEFAULT_PROJECT_CONTEXT in the frontend; fills gaps when a project has no settings yet.
DEFAULT_SETTINGS = {
    "tone": "Academic",
    "writing_style": "Formal",
    "academic_level": "Graduate",
    "language": "English",
    "essay_type": "Argumentative",
    "additional_instructions": None,
}
MAX_TITLE_LENGTH = 100
MAX_ADDITIONAL_INSTRUCTIONS_LENGTH = 110
MAX_DESCRIPTION_LENGTH = 255


def parse_settings(settings: Any) -> dict[str, Any]:
    """Validate a complete settings object; raises ValueError naming the bad field."""
    if not isinstance(settings, dict):
        raise ValueError("description must be an object or null.")

    values: dict[str, Any] = {}
    for field_name, allowed_values in SETTING_OPTIONS.items():
        value = settings.get(field_name)
        if value not in allowed_values:
            raise ValueError(f"description.{field_name} is invalid.")
        values[field_name] = value

    additional_instructions = settings.get("additional_instructions")
    if additional_instructions is not None and not isinstance(additional_instructions, str):
        raise ValueError("description.additional_instructions must be a string or null.")
    if isinstance(additional_instructions, str):
        additional_instructions = additional_instructions.strip() or None
        if (
            additional_instructions
            and len(additional_instructions) > MAX_ADDITIONAL_INSTRUCTIONS_LENGTH
        ):
            raise ValueError(
                "description.additional_instructions must be "
                f"{MAX_ADDITIONAL_INSTRUCTIONS_LENGTH} characters or fewer."
            )
    values["additional_instructions"] = additional_instructions

    if len(render_description(values)) > MAX_DESCRIPTION_LENGTH:
        raise ValueError(f"description must be {MAX_DESCRIPTION_LENGTH} characters or fewer.")
    return values


def render_description(settings: dict[str, Any]) -> str:
    return SystemPrompts.project_description(
        tone=settings["tone"],
        writing_style=settings["writing_style"],
        academic_level=settings["academic_level"],
        language=settings["language"],
        essay_type=settings["essay_type"],
        additional_instructions=settings.get("additional_instructions"),
    )


def parse_title(title: Any) -> str:
    if not isinstance(title, str) or not title.strip():
        raise ValueError("name is required.")
    title = title.strip()
    if len(title) > MAX_TITLE_LENGTH:
        raise ValueError(f"name must be {MAX_TITLE_LENGTH} characters or fewer.")
    return title


def update_project_settings(project_id: int, changes: dict[str, Any]) -> dict[str, Any]:
    """Apply a partial update of the title and/or writing settings.

    Raises ValueError with a message meant for the model when a value is rejected.
    """
    project = db.session.get(Project, project_id)
    if project is None:
        raise ValueError("Project not found.")
    if not isinstance(changes, dict) or not changes:
        raise ValueError("Give at least one setting to change.")

    unknown = set(changes) - {"title", *SETTING_OPTIONS, "additional_instructions"}
    if unknown:
        raise ValueError(f"Unknown setting: {', '.join(sorted(unknown))}.")

    # Validate everything before touching the project so a rejected value changes nothing.
    title = None
    if "title" in changes:
        try:
            title = parse_title(changes["title"])
        except ValueError as error:
            raise ValueError(str(error).replace("name", "title", 1)) from error

    settings = None
    setting_changes = {key: value for key, value in changes.items() if key != "title"}
    if setting_changes:
        current = {**DEFAULT_SETTINGS, **(project.settings or {})}
        try:
            settings = parse_settings({**current, **setting_changes})
        except ValueError as error:
            raise ValueError(str(error).replace("description.", "", 1)) from error

    if title is not None:
        project.name = title
    if settings is not None:
        project.settings = settings
        project.description = render_description(settings)

    try:
        db.session.commit()
    except IntegrityError as error:
        db.session.rollback()
        raise ValueError("Another project already uses this title.") from error

    return {
        "name": project.name,
        "description": project.description,
        "settings": project.settings,
    }


UPDATE_PROJECT_SETTINGS_TOOL = "update_project_settings"


def update_project_settings_tool() -> LocalTool:
    """The chat tool that lets the model correct the open project's title and writing settings."""
    properties: dict[str, Any] = {
        "title": {
            "type": "string",
            "description": f"The essay title (at most {MAX_TITLE_LENGTH} characters).",
        },
        **{
            field_name: {"type": "string", "enum": list(options)}
            for field_name, options in SETTING_OPTIONS.items()
        },
        "additional_instructions": {
            "type": "string",
            "description": (
                "Extra writing instructions for the project, at most "
                f"{MAX_ADDITIONAL_INSTRUCTIONS_LENGTH} characters. "
                "Replaces the current ones; an empty string removes them."
            ),
        },
    }
    return LocalTool(
        definition=ToolDefinition(
            name=UPDATE_PROJECT_SETTINGS_TOOL,
            description=(
                "Change the current project's title and/or writing settings (tone, writing "
                "style, academic level, language, essay type, additional instructions). "
                "Pass only the settings that should change; the others keep their values. "
                "Returns the project's updated title and settings."
            ),
            input_schema={
                "type": "object",
                "properties": properties,
                "additionalProperties": False,
            },
        ),
        run=update_project_settings,
    )
