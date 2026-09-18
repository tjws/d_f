"""create ai workflow runs

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-09-15
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, Sequence[str], None] = "d4e5f6a7b8c9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ai_workflow_runs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("customer_id", sa.Integer(), nullable=False),
        sa.Column("actor_user_id", sa.Integer(), nullable=True),
        sa.Column("goal", sa.String(length=20), nullable=False),
        sa.Column("provider_name", sa.String(length=30), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("result_json", sa.JSON(), nullable=True),
        sa.Column("error_code", sa.String(length=80), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("ai_workflow_runs") as batch_op:
        batch_op.create_index("ix_ai_workflow_runs_actor_created", ["actor_user_id", "created_at"])
        batch_op.create_index("ix_ai_workflow_runs_customer_status", ["customer_id", "status"])
        batch_op.create_index(batch_op.f("ix_ai_workflow_runs_customer_id"), ["customer_id"])
        batch_op.create_index(batch_op.f("ix_ai_workflow_runs_actor_user_id"), ["actor_user_id"])
        batch_op.create_index(batch_op.f("ix_ai_workflow_runs_status"), ["status"])


def downgrade() -> None:
    with op.batch_alter_table("ai_workflow_runs") as batch_op:
        batch_op.drop_index(batch_op.f("ix_ai_workflow_runs_status"))
        batch_op.drop_index(batch_op.f("ix_ai_workflow_runs_actor_user_id"))
        batch_op.drop_index(batch_op.f("ix_ai_workflow_runs_customer_id"))
        batch_op.drop_index("ix_ai_workflow_runs_customer_status")
        batch_op.drop_index("ix_ai_workflow_runs_actor_created")
    op.drop_table("ai_workflow_runs")
