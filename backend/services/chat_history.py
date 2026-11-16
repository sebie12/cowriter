"""Stores a project's chat messages and clears its chat."""

from datetime import datetime, timezone

from sqlalchemy.exc import SQLAlchemyError

from backend.database import Conversation, Message, ToolCall, db
from backend.services.conversation_service import ConversationService


def utc_from_iso(value: str | None) -> datetime:
    """Parse an event timestamp (ISO 8601, 'Z' allowed) into naive UTC, the DB's convention."""
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            parsed = None
        if parsed is not None:
            if parsed.tzinfo is not None:
                parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
            return parsed
    return datetime.now(timezone.utc).replace(tzinfo=None)


class ChatHistoryService:
    def __init__(self, conversations: ConversationService | None = None):
        self.conversations = conversations or ConversationService()

    def add_message(
        self,
        project_id: int,
        role: str,
        content: str,
        created_at: datetime | None = None,
    ) -> Message:
        conversation = self.conversations.get_or_create_for_project(project_id)
        message = Message(
            conversation_id=conversation.id,
            role=role,
            content=content,
            # Microsecond timestamps keep messages and tool calls in the order they happened.
            created_at=created_at or utc_from_iso(None),
        )
        db.session.add(message)
        self._commit()
        return message

    def timeline(self, project_id: int) -> list[dict]:
        """The project's saved messages and tool calls, oldest first, each tagged with its `kind`."""
        conversation_ids = [
            conversation_id
            for (conversation_id,) in db.session.query(Conversation.id).filter_by(project_id=project_id)
        ]
        if not conversation_ids:
            return []
        messages = Message.query.filter(Message.conversation_id.in_(conversation_ids)).all()
        tool_calls = ToolCall.query.filter(ToolCall.conversation_id.in_(conversation_ids)).all()
        items = [
            (message.created_at, 0, message.id, {"kind": "message", **message.to_dict()})
            for message in messages
        ] + [
            (tool_call.created_at, 1, tool_call.id, {"kind": "tool_call", **tool_call.to_dict()})
            for tool_call in tool_calls
        ]
        items.sort(key=lambda item: (item[0] or datetime.min, item[1], item[2]))
        return [item[3] for item in items]

    def clear(self, project_id: int) -> None:
        """Delete the project's chat: its conversations, messages, and tool calls."""
        conversation_ids = [
            conversation_id
            for (conversation_id,) in db.session.query(Conversation.id).filter_by(project_id=project_id)
        ]
        if conversation_ids:
            # Deleted explicitly: SQLite doesn't enforce the ON DELETE CASCADE foreign keys here.
            Message.query.filter(Message.conversation_id.in_(conversation_ids)).delete(
                synchronize_session=False
            )
            ToolCall.query.filter(ToolCall.conversation_id.in_(conversation_ids)).delete(
                synchronize_session=False
            )
            Conversation.query.filter(Conversation.id.in_(conversation_ids)).delete(
                synchronize_session=False
            )
        self._commit()
        db.session.expire_all()

    @staticmethod
    def _commit() -> None:
        try:
            db.session.commit()
        except SQLAlchemyError:
            db.session.rollback()
            raise
