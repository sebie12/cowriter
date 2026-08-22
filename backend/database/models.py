from .extensions import db


provider_auth_methods = db.Table(
    "provider_auth_methods",
    db.Column("provider_id", db.Integer, db.ForeignKey("providers.id"), primary_key=True),
    db.Column("auth_method_id", db.Integer, db.ForeignKey("auth_methods.id"), primary_key=True),
)


class ProviderConnection(db.Model):
    __tablename__ = "provider_connections"
    __table_args__ = (
        db.UniqueConstraint("provider", "account_id", name="uq_provider_connections_provider_account"),
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

    id = db.Column(db.Integer, primary_key=True)
    method_name = db.Column(db.String(50), nullable=False, unique=True)
    description = db.Column(db.String(255), nullable=True)

    providers = db.relationship(
        "Provider",
        secondary=provider_auth_methods,
        back_populates="auth_methods"
    )

    def __str__(self):
        return self.method_name
