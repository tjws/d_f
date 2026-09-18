"""create sales scripts

Revision ID: d8e9f0a1b2c3
Revises: c7d8e9f0a1b2
"""

from alembic import op
import sqlalchemy as sa


revision = "d8e9f0a1b2c3"
down_revision = "c7d8e9f0a1b2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sales_scripts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("scene", sa.String(length=50), nullable=False),
        sa.Column("customer_stage", sa.String(length=30), nullable=True),
        sa.Column("objection_type", sa.String(length=50), nullable=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("tone", sa.String(length=30), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("approved_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sales_scripts_scene", "sales_scripts", ["scene"], unique=False)
    op.create_index("ix_sales_scripts_customer_stage", "sales_scripts", ["customer_stage"], unique=False)
    op.create_index("ix_sales_scripts_status", "sales_scripts", ["status"], unique=False)
    op.create_index("ix_sales_scripts_created_by", "sales_scripts", ["created_by"], unique=False)
    op.create_index("ix_sales_scripts_approved_by", "sales_scripts", ["approved_by"], unique=False)
    op.create_index("ix_sales_scripts_status_scene", "sales_scripts", ["status", "scene"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_sales_scripts_status_scene", table_name="sales_scripts")
    op.drop_index("ix_sales_scripts_approved_by", table_name="sales_scripts")
    op.drop_index("ix_sales_scripts_created_by", table_name="sales_scripts")
    op.drop_index("ix_sales_scripts_status", table_name="sales_scripts")
    op.drop_index("ix_sales_scripts_customer_stage", table_name="sales_scripts")
    op.drop_index("ix_sales_scripts_scene", table_name="sales_scripts")
    op.drop_table("sales_scripts")
