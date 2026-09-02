"""Remove essays and add project language.

Revision ID: eb00b2f222d0
Revises: c74b6ac31e2d
Create Date: 2026-09-02 14:40:01.677780

"""

from alembic import op
import sqlalchemy as sa


revision = "eb00b2f222d0"
down_revision = "c74b6ac31e2d"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_table("essays")
    with op.batch_alter_table("projects") as batch_op:
        batch_op.add_column(
            sa.Column("language", sa.String(length=10), nullable=True)
        )


def downgrade():
    with op.batch_alter_table("projects") as batch_op:
        batch_op.drop_column("language")

    op.create_table(
        "essays",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name="fk_essays_project_id_projects",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", name="uq_essays_project_id"),
    )
    op.execute(
        "INSERT INTO essays (title, project_id, created_at, updated_at) "
        "SELECT name, id, created_at, updated_at FROM projects"
    )
