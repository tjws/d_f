"""expand AI feedback to profile, tag, reply and schedule targets

Revision ID: b1c2d3e4f5a6
Revises: a1b2c3d4e5f6
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "b1c2d3e4f5a6"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("ai_suggestion_feedback") as batch:
        batch.add_column(sa.Column("target_type", sa.String(length=30), nullable=True))
        batch.add_column(sa.Column("target_id", sa.String(length=100), nullable=True))
    op.execute("UPDATE ai_suggestion_feedback SET target_type = 'suggestion', target_id = CAST(suggestion_id AS VARCHAR) WHERE target_type IS NULL")
    with op.batch_alter_table("ai_suggestion_feedback") as batch:
        batch.alter_column("suggestion_id", existing_type=sa.Integer(), nullable=True)
        batch.alter_column("target_type", existing_type=sa.String(length=30), nullable=False)
        batch.alter_column("target_id", existing_type=sa.String(length=100), nullable=False)
        batch.drop_constraint("uq_ai_suggestion_feedback_suggestion", type_="unique")
        batch.create_unique_constraint("uq_ai_suggestion_feedback_target", ["target_type", "target_id"])
        batch.create_index("ix_ai_suggestion_feedback_target_type", ["target_type"])
        batch.create_index("ix_ai_suggestion_feedback_target_id", ["target_id"])


def downgrade() -> None:
    with op.batch_alter_table("ai_suggestion_feedback") as batch:
        batch.drop_index("ix_ai_suggestion_feedback_target_id")
        batch.drop_index("ix_ai_suggestion_feedback_target_type")
        batch.drop_constraint("uq_ai_suggestion_feedback_target", type_="unique")
        batch.create_unique_constraint("uq_ai_suggestion_feedback_suggestion", ["suggestion_id"])
        batch.drop_column("target_id")
        batch.drop_column("target_type")
        batch.alter_column("suggestion_id", existing_type=sa.Integer(), nullable=False)
