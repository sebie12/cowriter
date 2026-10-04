from datetime import datetime, timezone

from sqlalchemy.exc import SQLAlchemyError

if __package__ and __package__.startswith("backend."):
    from ..database import ToolCall, db
else:
    from database import ToolCall, db



class ToolCallService:
    def get_tool_call_by_id(self, tool_call_id):
        return db.session.get(ToolCall, tool_call_id)

    def start_tool_call(
        self,
        *,
        conversation_id,
        provider_call_id,
        tool_name,
        input_data,
    ):
        return self.create_tool_call(ToolCall(
            conversation_id=conversation_id,
            provider_call_id=provider_call_id,
            tool_name=tool_name,
            input_data=input_data,
            status="pending",
            created_at=self._utcnow(),
        ))

    def mark_tool_call_running(self, tool_call_id):
        return self.update_tool_call(tool_call_id, status="running")

    def complete_tool_call(
        self,
        tool_call_id,
        *,
        output_data,
        is_error=False,
        error=None,
    ):
        return self.update_tool_call(
            tool_call_id,
            output_data=output_data,
            status="failed" if is_error else "completed",
            error=(error or self._error_message(output_data)) if is_error else None,
            completed_at=self._utcnow(),
        )

    def fail_tool_call(self, tool_call_id, error):
        return self.update_tool_call(
            tool_call_id,
            status="failed",
            error=str(error),
            completed_at=self._utcnow(),
        )

    def create_tool_call(self, tool_call):
        db.session.add(tool_call)
        self._commit()
        return tool_call

    def update_tool_call(self, tool_call_id, **kwargs):
        tool_call = self.get_tool_call_by_id(tool_call_id)
        if tool_call:
            for key, value in kwargs.items():
                setattr(tool_call, key, value)
            self._commit()
        return tool_call

    def delete_tool_call(self, tool_call_id):
        tool_call = self.get_tool_call_by_id(tool_call_id)
        if tool_call:
            db.session.delete(tool_call)
            self._commit()
        return tool_call

    def get_all_tool_calls(self):
        return ToolCall.query.order_by(ToolCall.created_at.desc(), ToolCall.id.desc()).all()
    
    def get_tool_calls_by_conversation_id(self, conversation_id):
        return ToolCall.query.filter_by(conversation_id=conversation_id).order_by(ToolCall.created_at, ToolCall.id).all()

    @staticmethod
    def _utcnow():
        return datetime.now(timezone.utc).replace(tzinfo=None)

    @staticmethod
    def _error_message(output_data):
        if isinstance(output_data, dict):
            message = output_data.get("error")
            if isinstance(message, str):
                return message
        return "The tool returned an error."

    @staticmethod
    def _commit():
        try:
            db.session.commit()
        except SQLAlchemyError:
            db.session.rollback()
            raise
