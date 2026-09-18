"""add heartbeat timestamp for worker recovery

Revision ID: f8c9d0e1f2a3
Revises: f7b8c9d0e1f2
"""

from alembic import op
import sqlalchemy as sa


revision = "f8c9d0e1f2a3"
down_revision = "f7b8c9d0e1f2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "ai_workflow_runs",
        sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("ai_workflow_runs", "heartbeat_at")
