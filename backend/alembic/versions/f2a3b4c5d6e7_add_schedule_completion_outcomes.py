"""add schedule completion outcomes

Revision ID: f2a3b4c5d6e7
Revises: f1a2b3c4d5e6
"""

from alembic import op
import sqlalchemy as sa


revision = "f2a3b4c5d6e7"
down_revision = "f1a2b3c4d5e6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("schedules", sa.Column("outcome", sa.String(length=30), nullable=True))
    op.add_column("schedules", sa.Column("completion_note", sa.Text(), nullable=True))
    op.add_column("schedules", sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_schedules_outcome", "schedules", ["outcome"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_schedules_outcome", table_name="schedules")
    op.drop_column("schedules", "completed_at")
    op.drop_column("schedules", "completion_note")
    op.drop_column("schedules", "outcome")
