"""create ai suggestions

Revision ID: b8c2d3e4f5a6
Revises: a7b1c2d3e4f5
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b8c2d3e4f5a6"
down_revision: Union[str, None] = "a7b1c2d3e4f5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ai_suggestions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("customer_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("profile_id", sa.Integer(), nullable=True),
        sa.Column("suggestion_type", sa.String(length=30), nullable=False),
        sa.Column("content_json", sa.JSON(), nullable=False),
        sa.Column("edited_content_json", sa.JSON(), nullable=True),
        sa.Column("evidence_json", sa.JSON(), nullable=False),
        sa.Column("evidence_level", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("model_name", sa.String(length=100), nullable=False),
        sa.Column("model_version", sa.String(length=50), nullable=False),
        sa.Column("prompt_version", sa.String(length=50), nullable=False),
        sa.Column("decided_by", sa.Integer(), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["profile_id"], ["customer_profiles.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["decided_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("ai_suggestions", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_ai_suggestions_customer_id"), ["customer_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_ai_suggestions_user_id"), ["user_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_ai_suggestions_profile_id"), ["profile_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_ai_suggestions_status"), ["status"], unique=False)
        batch_op.create_index(batch_op.f("ix_ai_suggestions_decided_by"), ["decided_by"], unique=False)
        batch_op.create_index("ix_ai_suggestions_customer_status", ["customer_id", "status"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("ai_suggestions", schema=None) as batch_op:
        batch_op.drop_index("ix_ai_suggestions_customer_status")
        batch_op.drop_index(batch_op.f("ix_ai_suggestions_decided_by"))
        batch_op.drop_index(batch_op.f("ix_ai_suggestions_status"))
        batch_op.drop_index(batch_op.f("ix_ai_suggestions_profile_id"))
        batch_op.drop_index(batch_op.f("ix_ai_suggestions_user_id"))
        batch_op.drop_index(batch_op.f("ix_ai_suggestions_customer_id"))
    op.drop_table("ai_suggestions")
