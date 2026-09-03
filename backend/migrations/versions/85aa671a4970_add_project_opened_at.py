"""add project opened_at

Revision ID: 85aa671a4970
Revises: eb00b2f222d0
Create Date: 2026-09-03 12:15:18.238104

"""
from alembic import op
import sqlalchemy as sa


revision = "85aa671a4970"
down_revision = "eb00b2f222d0"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("projects") as batch_op:
        batch_op.add_column(sa.Column("opened_at", sa.DateTime(), nullable=True))


def downgrade():
    with op.batch_alter_table("projects") as batch_op:
        batch_op.drop_column("opened_at")
