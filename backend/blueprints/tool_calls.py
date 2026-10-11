from flask import Blueprint, jsonify

from backend.database import Conversation
from backend.services import ToolCallService

tool_calls_bp = Blueprint("tool_calls", __name__, url_prefix="/api/conversations")

@tool_calls_bp.get("/<int:conversation_id>/tool-calls")
def get_tool_calls_by_conversation_id(conversation_id):
    if Conversation.query.filter_by(id=conversation_id).first() is None:
        return jsonify({"error": "Conversation not found."}), 404

    tool_calls = ToolCallService().get_tool_calls_by_conversation_id(
        conversation_id=conversation_id
    )
    return jsonify([tool_call.to_dict() for tool_call in tool_calls]), 200
