"""create tags and customer tags

Revision ID: c9d3e4f5a6b7
Revises: b8c2d3e4f5a6
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c9d3e4f5a6b7"
down_revision: Union[str, None] = "b8c2d3e4f5a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tags",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("key", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("color", sa.String(length=20), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("tags", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_tags_key"), ["key"], unique=True)
        batch_op.create_index(batch_op.f("ix_tags_category"), ["category"], unique=False)
        batch_op.create_index(batch_op.f("ix_tags_status"), ["status"], unique=False)

    op.create_table(
        "customer_tags",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("customer_id", sa.Integer(), nullable=False),
        sa.Column("tag_id", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("evidence_json", sa.JSON(), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("confirmed_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tag_id"], ["tags.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["confirmed_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("customer_tags", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_customer_tags_customer_id"), ["customer_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_customer_tags_tag_id"), ["tag_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_customer_tags_status"), ["status"], unique=False)
        batch_op.create_index(batch_op.f("ix_customer_tags_created_by"), ["created_by"], unique=False)
        batch_op.create_index(batch_op.f("ix_customer_tags_confirmed_by"), ["confirmed_by"], unique=False)
        batch_op.create_index("ix_customer_tags_customer_status", ["customer_id", "status"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("customer_tags", schema=None) as batch_op:
        batch_op.drop_index("ix_customer_tags_customer_status")
        batch_op.drop_index(batch_op.f("ix_customer_tags_confirmed_by"))
        batch_op.drop_index(batch_op.f("ix_customer_tags_created_by"))
        batch_op.drop_index(batch_op.f("ix_customer_tags_status"))
        batch_op.drop_index(batch_op.f("ix_customer_tags_tag_id"))
        batch_op.drop_index(batch_op.f("ix_customer_tags_customer_id"))
    op.drop_table("customer_tags")
    with op.batch_alter_table("tags", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_tags_status"))
        batch_op.drop_index(batch_op.f("ix_tags_category"))
        batch_op.drop_index(batch_op.f("ix_tags_key"))
    op.drop_table("tags")
