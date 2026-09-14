"""create schedules

Revision ID: d4e5f6a7b8c9
Revises: c9d3e4f5a6b7
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, None] = "c9d3e4f5a6b7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "schedules",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("customer_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("suggestion_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("priority", sa.String(length=20), nullable=False),
        sa.Column("source", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("evidence_json", sa.JSON(), nullable=False),
        sa.Column("confirmed_by", sa.Integer(), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("wecom_calendar_id", sa.String(length=200), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["suggestion_id"], ["ai_suggestions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["confirmed_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("schedules", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_schedules_customer_id"), ["customer_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_schedules_user_id"), ["user_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_schedules_suggestion_id"), ["suggestion_id"], unique=True)
        batch_op.create_index(batch_op.f("ix_schedules_due_at"), ["due_at"], unique=False)
        batch_op.create_index(batch_op.f("ix_schedules_status"), ["status"], unique=False)
        batch_op.create_index(batch_op.f("ix_schedules_confirmed_by"), ["confirmed_by"], unique=False)
        batch_op.create_index("ix_schedules_customer_status", ["customer_id", "status"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("schedules", schema=None) as batch_op:
        batch_op.drop_index("ix_schedules_customer_status")
        batch_op.drop_index(batch_op.f("ix_schedules_confirmed_by"))
        batch_op.drop_index(batch_op.f("ix_schedules_status"))
        batch_op.drop_index(batch_op.f("ix_schedules_due_at"))
        batch_op.drop_index(batch_op.f("ix_schedules_suggestion_id"))
        batch_op.drop_index(batch_op.f("ix_schedules_user_id"))
        batch_op.drop_index(batch_op.f("ix_schedules_customer_id"))
    op.drop_table("schedules")
