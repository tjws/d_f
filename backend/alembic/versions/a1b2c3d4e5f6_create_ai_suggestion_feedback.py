"""create AI suggestion feedback

Revision ID: a1b2c3d4e5f6
Revises: f6a7b8c9d0e1
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "f6a7b8c9d0e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ai_suggestion_feedback",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("suggestion_id", sa.Integer(), nullable=False),
        sa.Column("customer_id", sa.Integer(), nullable=False),
        sa.Column("actor_user_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(length=20), nullable=False),
        sa.Column("edited_content", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["suggestion_id"], ["ai_suggestions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("suggestion_id", name="uq_ai_suggestion_feedback_suggestion"),
    )
    op.create_index("ix_ai_suggestion_feedback_suggestion_id", "ai_suggestion_feedback", ["suggestion_id"])
    op.create_index("ix_ai_suggestion_feedback_customer_id", "ai_suggestion_feedback", ["customer_id"])
    op.create_index("ix_ai_suggestion_feedback_actor_user_id", "ai_suggestion_feedback", ["actor_user_id"])
    op.create_index("ix_ai_suggestion_feedback_created_at", "ai_suggestion_feedback", ["created_at"])


def downgrade() -> None:
    op.drop_table("ai_suggestion_feedback")
