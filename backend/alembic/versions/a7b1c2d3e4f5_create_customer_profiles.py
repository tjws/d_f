"""create customer profiles

Revision ID: a7b1c2d3e4f5
Revises: c1801e192118
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a7b1c2d3e4f5"
down_revision: Union[str, None] = "c1801e192118"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "customer_profiles",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("customer_id", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("dimensions_json", sa.JSON(), nullable=False),
        sa.Column("evidence_json", sa.JSON(), nullable=False),
        sa.Column("model_name", sa.String(length=100), nullable=False),
        sa.Column("model_version", sa.String(length=50), nullable=False),
        sa.Column("prompt_version", sa.String(length=50), nullable=False),
        sa.Column("confirmed_by", sa.Integer(), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["confirmed_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("customer_id", "version", name="uq_customer_profiles_customer_version"),
    )
    with op.batch_alter_table("customer_profiles", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_customer_profiles_customer_id"), ["customer_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_customer_profiles_status"), ["status"], unique=False)
        batch_op.create_index(batch_op.f("ix_customer_profiles_confirmed_by"), ["confirmed_by"], unique=False)
        batch_op.create_index("ix_customer_profiles_customer_status", ["customer_id", "status"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("customer_profiles", schema=None) as batch_op:
        batch_op.drop_index("ix_customer_profiles_customer_status")
        batch_op.drop_index(batch_op.f("ix_customer_profiles_confirmed_by"))
        batch_op.drop_index(batch_op.f("ix_customer_profiles_status"))
        batch_op.drop_index(batch_op.f("ix_customer_profiles_customer_id"))
    op.drop_table("customer_profiles")
