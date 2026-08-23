"""Create the initial schema.

Revision ID: b007dbced275
Revises:
Create Date: 2026-08-23 09:54:11.132848
"""

from alembic import op
import sqlalchemy as sa


revision = "b007dbced275"
down_revision = None
branch_labels = None
depends_on = None


def _table_names(inspector):
    return set(inspector.get_table_names())


def _column_names(inspector, table_name):
    return {column["name"] for column in inspector.get_columns(table_name)}


def _index_names(inspector, table_name):
    return {index["name"] for index in inspector.get_indexes(table_name)}


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = _table_names(inspector)

    if "auth_methods" not in tables:
        op.create_table(
            "auth_methods",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("method_name", sa.String(length=50), nullable=False),
            sa.Column("description", sa.String(length=255), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_auth_methods_method_name",
            "auth_methods",
            ["method_name"],
            unique=True,
        )
    elif "ix_auth_methods_method_name" not in _index_names(inspector, "auth_methods"):
        op.create_index(
            "ix_auth_methods_method_name",
            "auth_methods",
            ["method_name"],
            unique=True,
        )

    if "projects" not in tables:
        op.create_table(
            "projects",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(length=100), nullable=False),
            sa.Column("description", sa.String(length=255), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("name"),
        )

    if "providers" not in tables:
        op.create_table(
            "providers",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(length=50), nullable=False),
            sa.Column("description", sa.String(length=255), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("name"),
        )

    if "essays" not in tables:
        op.create_table(
            "essays",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("title", sa.String(length=200), nullable=False),
            sa.Column("project_id", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
            sa.PrimaryKeyConstraint("id"),
        )

    if "provider_auth_methods" not in tables:
        op.create_table(
            "provider_auth_methods",
            sa.Column("provider_id", sa.Integer(), nullable=False),
            sa.Column("auth_method_id", sa.Integer(), nullable=False),
            sa.ForeignKeyConstraint(["auth_method_id"], ["auth_methods.id"]),
            sa.ForeignKeyConstraint(["provider_id"], ["providers.id"]),
            sa.PrimaryKeyConstraint("provider_id", "auth_method_id"),
        )

    if "provider_connections" not in tables:
        op.create_table(
            "provider_connections",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("provider", sa.String(length=50), nullable=False),
            sa.Column("account_id", sa.String(length=100), nullable=False),
            sa.Column("account_label", sa.String(length=100), nullable=False),
            sa.Column("endpoint_url", sa.String(length=2048), nullable=True),
            sa.Column("status", sa.String(length=20), nullable=False),
            sa.Column("expires_at", sa.DateTime(), nullable=True),
            sa.Column("auth_method_id", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["auth_method_id"], ["auth_methods.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "uq_provider_connections_provider_account",
            "provider_connections",
            ["provider", "account_id"],
            unique=True,
        )
    else:
        columns = _column_names(inspector, "provider_connections")
        if "endpoint_url" not in columns:
            op.add_column(
                "provider_connections",
                sa.Column("endpoint_url", sa.String(length=2048), nullable=True),
            )
        if (
            "uq_provider_connections_provider_account"
            not in _index_names(inspector, "provider_connections")
        ):
            bind.execute(
                sa.text(
                    "DELETE FROM provider_connections "
                    "WHERE id NOT IN ("
                    "SELECT MAX(id) FROM provider_connections "
                    "GROUP BY provider, account_id)"
                )
            )
            op.create_index(
                "uq_provider_connections_provider_account",
                "provider_connections",
                ["provider", "account_id"],
                unique=True,
            )

    if "conversations" not in tables:
        op.create_table(
            "conversations",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("essay_id", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["essay_id"], ["essays.id"]),
            sa.PrimaryKeyConstraint("id"),
        )

    if "messages" not in tables:
        op.create_table(
            "messages",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("role", sa.String(length=20), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("conversation_id", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(
                ["conversation_id"],
                ["conversations.id"],
                ondelete="CASCADE",
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_messages_conversation_id",
            "messages",
            ["conversation_id"],
            unique=False,
        )
        return

    message_columns = _column_names(inspector, "messages")
    if "conversation_id" not in message_columns:
        message_count = bind.execute(sa.text("SELECT COUNT(*) FROM messages")).scalar_one()
        if message_count:
            raise RuntimeError(
                "Cannot assign legacy messages to conversations automatically. "
                "Back up and resolve the orphaned messages before upgrading."
            )
        with op.batch_alter_table("messages") as batch_op:
            batch_op.add_column(
                sa.Column("conversation_id", sa.Integer(), nullable=False)
            )
            batch_op.create_foreign_key(
                "fk_messages_conversation_id_conversations",
                "conversations",
                ["conversation_id"],
                ["id"],
                ondelete="CASCADE",
            )
            batch_op.create_index(
                "ix_messages_conversation_id",
                ["conversation_id"],
                unique=False,
            )
    elif "ix_messages_conversation_id" not in _index_names(inspector, "messages"):
        op.create_index(
            "ix_messages_conversation_id",
            "messages",
            ["conversation_id"],
            unique=False,
        )


def downgrade():
    op.drop_table("messages")
    op.drop_table("conversations")
    op.drop_table("provider_connections")
    op.drop_table("provider_auth_methods")
    op.drop_table("essays")
    op.drop_table("providers")
    op.drop_table("projects")
    op.drop_table("auth_methods")
