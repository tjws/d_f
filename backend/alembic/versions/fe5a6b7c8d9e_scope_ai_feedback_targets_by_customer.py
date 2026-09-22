"""scope AI feedback targets by customer

Revision ID: fe5a6b7c8d9e
Revises: fd4e5f6a7b8c
"""

from alembic import op


revision = "fe5a6b7c8d9e"
down_revision = "fd4e5f6a7b8c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 历史数据恢复后，资源编号可能在不同客户范围内重复；反馈必须按客户隔离。
    with op.batch_alter_table("ai_suggestion_feedback") as batch:
        batch.drop_constraint("uq_ai_suggestion_feedback_target", type_="unique")
        batch.create_unique_constraint(
            "uq_ai_suggestion_feedback_customer_target",
            ["customer_id", "target_type", "target_id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("ai_suggestion_feedback") as batch:
        batch.drop_constraint("uq_ai_suggestion_feedback_customer_target", type_="unique")
        batch.create_unique_constraint(
            "uq_ai_suggestion_feedback_target",
            ["target_type", "target_id"],
        )
