"""Move conversations from essays to projects.

Revision ID: 86d1e2f922f7
Revises: b007dbced275
Create Date: 2026-08-23 10:30:40.499151
"""

from alembic import op
import sqlalchemy as sa


revision = "86d1e2f922f7"
down_revision = "b007dbced275"
branch_labels = None
depends_on = None


NAMING_CONVENTION = {
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
}


def _set_sqlite_foreign_keys(enabled):
    if op.get_bind().dialect.name != "sqlite":
        return

    value = "ON" if enabled else "OFF"
    with op.get_context().autocommit_block():
        op.execute(f"PRAGMA foreign_keys={value}")


def _check_sqlite_foreign_keys():
    if op.get_bind().dialect.name != "sqlite":
        return

    violation = op.get_bind().execute(sa.text("PRAGMA foreign_key_check")).first()
    if violation:
        raise RuntimeError(f"Foreign key violation after migration: {violation}")


def upgrade():
    bind = op.get_bind()
    duplicate_essay = bind.execute(
        sa.text(
            "SELECT project_id FROM essays "
            "GROUP BY project_id HAVING COUNT(*) > 1 LIMIT 1"
        )
    ).first()
    if duplicate_essay:
        raise RuntimeError(
            f"Project {duplicate_essay.project_id} has multiple essays. "
            "Resolve the duplicate essays before upgrading."
        )

    op.add_column(
        "conversations",
        sa.Column("project_id", sa.Integer(), nullable=True),
    )
    bind.execute(
        sa.text(
            "UPDATE conversations SET project_id = ("
            "SELECT essays.project_id FROM essays "
            "WHERE essays.id = conversations.essay_id)"
        )
    )
    orphaned_conversation = bind.execute(
        sa.text(
            "SELECT id FROM conversations WHERE project_id IS NULL LIMIT 1"
        )
    ).first()
    if orphaned_conversation:
        raise RuntimeError(
            f"Conversation {orphaned_conversation.id} has no project. "
            "Repair its essay relationship before upgrading."
        )

    _set_sqlite_foreign_keys(False)
    with op.batch_alter_table(
        "essays",
        naming_convention=NAMING_CONVENTION,
    ) as batch_op:
        batch_op.drop_constraint(
            "fk_essays_project_id_projects",
            type_="foreignkey",
        )
        batch_op.create_foreign_key(
            "fk_essays_project_id_projects",
            "projects",
            ["project_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch_op.create_unique_constraint(
            "uq_essays_project_id",
            ["project_id"],
        )

    with op.batch_alter_table(
        "conversations",
        naming_convention=NAMING_CONVENTION,
    ) as batch_op:
        batch_op.drop_constraint(
            "fk_conversations_essay_id_essays",
            type_="foreignkey",
        )
        batch_op.create_foreign_key(
            "fk_conversations_project_id_projects",
            "projects",
            ["project_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch_op.alter_column(
            "project_id",
            existing_type=sa.Integer(),
            nullable=False,
        )
        batch_op.create_index(
            "ix_conversations_project_id",
            ["project_id"],
            unique=False,
        )
        batch_op.drop_column("essay_id")

    _set_sqlite_foreign_keys(True)
    _check_sqlite_foreign_keys()


def downgrade():
    bind = op.get_bind()
    op.add_column(
        "conversations",
        sa.Column("essay_id", sa.Integer(), nullable=True),
    )
    bind.execute(
        sa.text(
            "UPDATE conversations SET essay_id = ("
            "SELECT essays.id FROM essays "
            "WHERE essays.project_id = conversations.project_id)"
        )
    )
    conversation_without_essay = bind.execute(
        sa.text(
            "SELECT id FROM conversations WHERE essay_id IS NULL LIMIT 1"
        )
    ).first()
    if conversation_without_essay:
        raise RuntimeError(
            f"Conversation {conversation_without_essay.id} belongs to a project "
            "without an essay and cannot be downgraded."
        )

    _set_sqlite_foreign_keys(False)
    with op.batch_alter_table(
        "conversations",
        naming_convention=NAMING_CONVENTION,
    ) as batch_op:
        batch_op.drop_constraint(
            "fk_conversations_project_id_projects",
            type_="foreignkey",
        )
        batch_op.create_foreign_key(
            "fk_conversations_essay_id_essays",
            "essays",
            ["essay_id"],
            ["id"],
        )
        batch_op.alter_column(
            "essay_id",
            existing_type=sa.Integer(),
            nullable=False,
        )
        batch_op.drop_index("ix_conversations_project_id")
        batch_op.drop_column("project_id")

    with op.batch_alter_table(
        "essays",
        naming_convention=NAMING_CONVENTION,
    ) as batch_op:
        batch_op.drop_constraint(
            "fk_essays_project_id_projects",
            type_="foreignkey",
        )
        batch_op.create_foreign_key(
            "fk_essays_project_id_projects",
            "projects",
            ["project_id"],
            ["id"],
        )
        batch_op.drop_constraint(
            "uq_essays_project_id",
            type_="unique",
        )

    _set_sqlite_foreign_keys(True)
    _check_sqlite_foreign_keys()
