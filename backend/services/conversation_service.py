from sqlalchemy.exc import SQLAlchemyError

if __package__ and __package__.startswith("backend."):
    from ..database import Conversation, db
else:
    from database import Conversation, db


class ConversationService:
    def get_or_create_for_project(self, project_id):
        conversation = (
            Conversation.query
            .filter_by(project_id=project_id)
            .order_by(Conversation.created_at.desc(), Conversation.id.desc())
            .first()
        )
        if conversation is not None:
            return conversation

        conversation = Conversation(project_id=project_id)
        db.session.add(conversation)
        try:
            db.session.commit()
        except SQLAlchemyError:
            db.session.rollback()
            raise
        return conversation
