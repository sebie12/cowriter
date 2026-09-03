from .extensions import db


def _isoformat(value):
    return value.isoformat() if value else None


provider_auth_methods = db.Table(
    "provider_auth_methods",
    db.Column("provider_id", db.Integer, db.ForeignKey("providers.id"), primary_key=True),
    db.Column("auth_method_id", db.Integer, db.ForeignKey("auth_methods.id"), primary_key=True),
)


class ProviderConnection(db.Model):
    __tablename__ = "provider_connections"
    __table_args__ = (
        db.Index(
            "uq_provider_connections_provider_account",
            "provider",
            "account_id",
            unique=True,
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    provider = db.Column(db.String(50), nullable=False)
    account_id = db.Column(db.String(100), nullable=False)
    account_label = db.Column(db.String(100), nullable=False)
    endpoint_url = db.Column(db.String(2048), nullable=True)
    status = db.Column(db.String(20), nullable=False, default="disconnected")
    expires_at = db.Column(db.DateTime, nullable=True)

    auth_method_id = db.Column(
        db.Integer,
        db.ForeignKey("auth_methods.id"),
        nullable=False)
    auth_method = db.relationship("AuthMethod")

    created_at = db.Column(
        db.DateTime,
        default=db.func.current_timestamp()
    )

    updated_at = db.Column(
        db.DateTime,
        default=db.func.current_timestamp(),
        onupdate=db.func.current_timestamp()
    )


class Provider(db.Model):
    __tablename__ = "providers"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    description = db.Column(db.String(255), nullable=True)

    auth_methods = db.relationship(
        "AuthMethod",
        secondary=provider_auth_methods,
        back_populates="providers"
    )

    def __str__(self):
        return self.name


class AuthMethod(db.Model):
    __tablename__ = "auth_methods"
    __table_args__ = (
        db.Index("ix_auth_methods_method_name", "method_name", unique=True),
    )

    id = db.Column(db.Integer, primary_key=True)
    method_name = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(255), nullable=True)

    providers = db.relationship(
        "Provider",
        secondary=provider_auth_methods,
        back_populates="auth_methods"
    )

    def __str__(self):
        return self.method_name

class Project(db.Model):
    __tablename__ = "projects"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.String(255), nullable=True)
    path = db.Column(db.String(255), nullable=True, unique=True)
    language = db.Column(db.String(10), nullable=True, default="en")

    conversations = db.relationship(
        "Conversation",
        back_populates="project",
        cascade="all, delete-orphan",
        order_by=lambda: (Conversation.created_at, Conversation.id),
        passive_deletes=True,
    )

    created_at = db.Column(
        db.DateTime,
        default=db.func.current_timestamp()
    )

    opened_at = db.Column(
        db.DateTime,
        default=db.func.current_timestamp()
    )

    updated_at = db.Column(
        db.DateTime,
        default=db.func.current_timestamp(),
        onupdate=db.func.current_timestamp()
    )

    def __str__(self):
        return self.name

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "conversations": [
                conversation.to_dict() for conversation in self.conversations
            ],
            "path": self.path,
            "created_at": _isoformat(self.created_at),
            "updated_at": _isoformat(self.updated_at),
            "opened_at": _isoformat(self.opened_at),
        }

class Conversation(db.Model):
    __tablename__ = "conversations"

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(
        db.Integer,
        db.ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    project = db.relationship("Project", back_populates="conversations")

    messages = db.relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by=lambda: (Message.created_at, Message.id),
        passive_deletes=True,
    )

    created_at = db.Column(
        db.DateTime,
        default=db.func.current_timestamp()
    )

    updated_at = db.Column(
        db.DateTime,
        default=db.func.current_timestamp(),
        onupdate=db.func.current_timestamp()
    )

    def __str__(self):
        return f"Conversation {self.id} in Project {self.project_id}"

    def to_dict(self):
        return {
            "id": self.id,
            "project_id": self.project_id,
            "messages": [message.to_dict() for message in self.messages],
            "created_at": _isoformat(self.created_at),
            "updated_at": _isoformat(self.updated_at),
        }


class Message(db.Model):
    __tablename__ = "messages"

    id = db.Column(db.Integer, primary_key=True)
    role = db.Column(db.String(20), nullable=False)
    content = db.Column(db.Text, nullable=False)

    conversation_id = db.Column(
        db.Integer,
        db.ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    conversation = db.relationship("Conversation", back_populates="messages")

    created_at = db.Column(
        db.DateTime,
        default=db.func.current_timestamp()
    )

    updated_at = db.Column(
        db.DateTime,
        default=db.func.current_timestamp(),
        onupdate=db.func.current_timestamp()
    )

    def __str__(self):
        return f"Message {self.id} in Conversation {self.conversation_id}"

    def to_dict(self):
        return {
            "id": self.id,
            "conversation_id": self.conversation_id,
            "role": self.role,
            "content": self.content,
            "created_at": _isoformat(self.created_at),
            "updated_at": _isoformat(self.updated_at),
        }
