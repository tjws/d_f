"""remove redundant external id constraints

Revision ID: e9f0a1b2c3d4
Revises: d8e9f0a1b2c3

The initial order/ticket migrations created both a unique constraint and a
unique index.  The model now intentionally keeps the unique index only.
"""

from alembic import op
from sqlalchemy import inspect


revision = "e9f0a1b2c3d4"
down_revision = "d8e9f0a1b2c3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # PostgreSQL gives the implicit constraints stable names. SQLite's test
    # path does not expose the same names, so it keeps the original constraint
    # while using the model's equivalent unique index for new databases.
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    inspector = inspect(bind)
    for table_name, constraint_name in (
        ("course_orders", "course_orders_external_order_id_key"),
        ("service_tickets", "service_tickets_external_ticket_id_key"),
    ):
        names = {item.get("name") for item in inspector.get_unique_constraints(table_name)}
        if constraint_name in names:
            op.drop_constraint(constraint_name, table_name=table_name, type_="unique")


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.create_unique_constraint("course_orders_external_order_id_key", "course_orders", ["external_order_id"])
        op.create_unique_constraint("service_tickets_external_ticket_id_key", "service_tickets", ["external_ticket_id"])
