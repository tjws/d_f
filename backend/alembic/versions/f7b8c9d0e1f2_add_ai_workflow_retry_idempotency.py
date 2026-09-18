"""add AI workflow retry and idempotency metadata

Revision ID: f7b8c9d0e1f2
Revises: f3a4b5c6d7e8
Create Date: 2026-09-16
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "f7b8c9d0e1f2"
down_revision: Union[str, Sequence[str], None] = "f3a4b5c6d7e8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "ai_workflow_runs",
        sa.Column("idempotency_key", sa.String(length=100), nullable=True),
    )
    op.create_index(
        "uq_ai_workflow_runs_actor_idempotency",
        "ai_workflow_runs",
        ["actor_user_id", "idempotency_key"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_ai_workflow_runs_actor_idempotency", table_name="ai_workflow_runs")
    op.drop_column("ai_workflow_runs", "idempotency_key")
