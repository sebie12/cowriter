from flask import Blueprint, jsonify, request
from sqlalchemy.exc import IntegrityError

if __package__ and __package__.startswith("backend."):
    from ..database import Conversation, Message, Project, db
else:
    from database import Conversation, Message, Project, db


conversations_bp = Blueprint(
    "conversations",
    __name__,
    url_prefix="/api/projects/conversations",
)
ALLOWED_MESSAGE_ROLES = {"system", "user", "assistant"}

