"""Add tool call execution state.

Revision ID: 7ea2cba304c1
Revises: 24c85e7040c9
Create Date: 2026-09-19 00:01:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "7ea2cba304c1"
down_revision = "24c85e7040c9"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("tool_calls") as batch_op:
        batch_op.add_column(
            sa.Column("provider_call_id", sa.String(length=255), nullable=True)
        )
        batch_op.add_column(
            sa.Column(
                "status",
                sa.String(length=20),
                server_default="pending",
                nullable=False,
            )
        )
        batch_op.add_column(sa.Column("error", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("completed_at", sa.DateTime(), nullable=True))


def downgrade():
    with op.batch_alter_table("tool_calls") as batch_op:
        batch_op.drop_column("completed_at")
        batch_op.drop_column("error")
        batch_op.drop_column("status")
        batch_op.drop_column("provider_call_id")
