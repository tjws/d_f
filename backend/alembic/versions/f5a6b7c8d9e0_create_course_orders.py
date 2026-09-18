"""create course orders

Revision ID: f5a6b7c8d9e0
Revises: e4f5a6b7c8d9
"""

from alembic import op
import sqlalchemy as sa


revision = "f5a6b7c8d9e0"
down_revision = "e4f5a6b7c8d9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "course_orders",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("external_order_id", sa.String(length=100), nullable=False),
        sa.Column("customer_id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=True),
        sa.Column("course_name", sa.String(length=200), nullable=False),
        sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("ordered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("raw_snapshot_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("external_order_id"),
    )
    op.create_index("ix_course_orders_external_order_id", "course_orders", ["external_order_id"], unique=True)
    op.create_index("ix_course_orders_customer_id", "course_orders", ["customer_id"], unique=False)
    op.create_index("ix_course_orders_student_id", "course_orders", ["student_id"], unique=False)
    op.create_index("ix_course_orders_status", "course_orders", ["status"], unique=False)
    op.create_index("ix_course_orders_ordered_at", "course_orders", ["ordered_at"], unique=False)
    op.create_index("ix_course_orders_customer_status", "course_orders", ["customer_id", "status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_course_orders_customer_status", table_name="course_orders")
    op.drop_index("ix_course_orders_ordered_at", table_name="course_orders")
    op.drop_index("ix_course_orders_status", table_name="course_orders")
    op.drop_index("ix_course_orders_student_id", table_name="course_orders")
    op.drop_index("ix_course_orders_customer_id", table_name="course_orders")
    op.drop_index("ix_course_orders_external_order_id", table_name="course_orders")
    op.drop_table("course_orders")
