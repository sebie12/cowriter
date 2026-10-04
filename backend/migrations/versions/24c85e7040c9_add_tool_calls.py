"""Add tool calls.

Revision ID: 24c85e7040c9
Revises: 85aa671a4970
Create Date: 2026-09-19 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "24c85e7040c9"
down_revision = "85aa671a4970"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "tool_calls",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tool_name", sa.String(length=100), nullable=False),
        sa.Column("input_data", sa.JSON(), nullable=False),
        sa.Column("output_data", sa.JSON(), nullable=True),
        sa.Column("conversation_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["conversations.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_tool_calls_conversation_id",
        "tool_calls",
        ["conversation_id"],
        unique=False,
    )


def downgrade():
    op.drop_index("ix_tool_calls_conversation_id", table_name="tool_calls")
    op.drop_table("tool_calls")
