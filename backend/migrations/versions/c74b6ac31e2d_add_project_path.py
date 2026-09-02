"""Add project directory path.

Revision ID: c74b6ac31e2d
Revises: 86d1e2f922f7
Create Date: 2026-09-01 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "c74b6ac31e2d"
down_revision = "86d1e2f922f7"
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
    _set_sqlite_foreign_keys(False)
    with op.batch_alter_table(
        "projects",
        naming_convention=NAMING_CONVENTION,
    ) as batch_op:
        batch_op.add_column(sa.Column("path", sa.String(length=255), nullable=True))
        batch_op.create_unique_constraint("uq_projects_path", ["path"])
    _set_sqlite_foreign_keys(True)
    _check_sqlite_foreign_keys()


def downgrade():
    _set_sqlite_foreign_keys(False)
    with op.batch_alter_table(
        "projects",
        naming_convention=NAMING_CONVENTION,
    ) as batch_op:
        batch_op.drop_constraint("uq_projects_path", type_="unique")
        batch_op.drop_column("path")
    _set_sqlite_foreign_keys(True)
    _check_sqlite_foreign_keys()
