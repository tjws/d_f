"""add student archive timestamp

Revision ID: c2d3e4f5a6b7
Revises: b1c2d3e4f5a6
"""

from alembic import op
import sqlalchemy as sa


revision = "c2d3e4f5a6b7"
down_revision = "b1c2d3e4f5a6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("students", sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_students_archived_at", "students", ["archived_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_students_archived_at", table_name="students")
    op.drop_column("students", "archived_at")
