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
    # Structured writing settings; `description` is the prose rendered from them.
    settings = db.Column(db.JSON, nullable=True)
    draft = db.Column(db.JSON, nullable=True)

    conversations = db.relationship(
        "Conversation",
        back_populates="project",
        cascade="all, delete-orphan",
        order_by=lambda: (Conversation.created_at, Conversation.id),
        passive_deletes=True,
    )

    references = db.relationship(
        "Reference",
        back_populates="project",
        cascade="all, delete-orphan",
        order_by=lambda: (Reference.created_at, Reference.id),
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
            "settings": self.settings,
            "conversations": [
                conversation.to_dict() for conversation in self.conversations
            ],
            "path": self.path,
            "draft": self.draft,
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

    tool_calls = db.relationship(
        "ToolCall",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by=lambda: (ToolCall.created_at, ToolCall.id),
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
            "tool_calls": [tool_call.to_dict() for tool_call in self.tool_calls],
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

class ToolCall(db.Model):
    __tablename__ = "tool_calls"

    id = db.Column(db.Integer, primary_key=True)
    provider_call_id = db.Column(db.String(255), nullable=True)
    tool_name = db.Column(db.String(100), nullable=False)
    input_data = db.Column(db.JSON, nullable=False)
    output_data = db.Column(db.JSON, nullable=True)
    status = db.Column(db.String(20), nullable=False, default="pending")
    error = db.Column(db.Text, nullable=True)

    conversation_id = db.Column(
        db.Integer,
        db.ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    conversation = db.relationship("Conversation", back_populates="tool_calls")

    created_at = db.Column(
        db.DateTime,
        default=db.func.current_timestamp()
    )
    completed_at = db.Column(db.DateTime, nullable=True)

    def __str__(self):
        return f"Tool Call {self.id} in Conversation {self.conversation_id}"

    def to_dict(self):
        return {
            "id": self.id,
            "conversation_id": self.conversation_id,
            "provider_call_id": self.provider_call_id,
            "tool_name": self.tool_name,
            "input_data": self.input_data,
            "output_data": self.output_data,
            "status": self.status,
            "error": self.error,
            "created_at": _isoformat(self.created_at),
            "completed_at": _isoformat(self.completed_at),
        }


class Reference(db.Model):
    __tablename__ = "references"
    __table_args__ = (
        db.Index(
            "uq_references_project_paper",
            "project_id",
            "paper_id",
            unique=True,
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(
        db.Integer,
        db.ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    project = db.relationship("Project", back_populates="references")

    paper_id = db.Column(db.String(100), nullable=False)
    title = db.Column(db.String(1000), nullable=False)
    year = db.Column(db.Integer, nullable=True)
    authors = db.Column(db.JSON, nullable=False, default=list)
    venue = db.Column(db.String(500), nullable=True)
    abstract = db.Column(db.Text, nullable=True)
    tldr = db.Column(db.Text, nullable=True)
    url = db.Column(db.String(2048), nullable=True)
    pdf_url = db.Column(db.String(2048), nullable=True)
    doi = db.Column(db.String(255), nullable=True)
    citation_count = db.Column(db.Integer, nullable=True)

    created_at = db.Column(
        db.DateTime,
        default=db.func.current_timestamp()
    )

    def __str__(self):
        return self.title

    def to_dict(self):
        return {
            "id": self.id,
            "project_id": self.project_id,
            "paper_id": self.paper_id,
            "title": self.title,
            "year": self.year,
            "authors": list(self.authors or []),
            "venue": self.venue,
            "abstract": self.abstract,
            "tldr": self.tldr,
            "url": self.url,
            "pdf_url": self.pdf_url,
            "doi": self.doi,
            "citation_count": self.citation_count,
            "created_at": _isoformat(self.created_at),
        }
