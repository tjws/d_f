"""align external identifier indexes with unique model constraints

Revision ID: b6c7d8e9f0a1
Revises: a6b7c8d9e0f1
"""

from alembic import op


revision = "b6c7d8e9f0a1"
down_revision = "a6b7c8d9e0f1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index("ix_course_orders_external_order_id", table_name="course_orders")
    op.create_index("ix_course_orders_external_order_id", "course_orders", ["external_order_id"], unique=True)
    op.drop_index("ix_service_tickets_external_ticket_id", table_name="service_tickets")
    op.create_index("ix_service_tickets_external_ticket_id", "service_tickets", ["external_ticket_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_service_tickets_external_ticket_id", table_name="service_tickets")
    op.create_index("ix_service_tickets_external_ticket_id", "service_tickets", ["external_ticket_id"], unique=False)
    op.drop_index("ix_course_orders_external_order_id", table_name="course_orders")
    op.create_index("ix_course_orders_external_order_id", "course_orders", ["external_order_id"], unique=False)
