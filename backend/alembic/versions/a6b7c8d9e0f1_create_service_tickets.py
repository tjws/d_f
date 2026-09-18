"""create service tickets

Revision ID: a6b7c8d9e0f1
Revises: f5a6b7c8d9e0
"""

from alembic import op
import sqlalchemy as sa


revision = "a6b7c8d9e0f1"
down_revision = "f5a6b7c8d9e0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "service_tickets",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("external_ticket_id", sa.String(length=100), nullable=False),
        sa.Column("customer_id", sa.Integer(), nullable=False),
        sa.Column("type", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("summary_encrypted", sa.Text(), nullable=False),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("raw_snapshot_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("external_ticket_id"),
    )
    op.create_index("ix_service_tickets_external_ticket_id", "service_tickets", ["external_ticket_id"], unique=True)
    op.create_index("ix_service_tickets_customer_id", "service_tickets", ["customer_id"], unique=False)
    op.create_index("ix_service_tickets_status", "service_tickets", ["status"], unique=False)
    op.create_index("ix_service_tickets_opened_at", "service_tickets", ["opened_at"], unique=False)
    op.create_index("ix_service_tickets_customer_status", "service_tickets", ["customer_id", "status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_service_tickets_customer_status", table_name="service_tickets")
    op.drop_index("ix_service_tickets_opened_at", table_name="service_tickets")
    op.drop_index("ix_service_tickets_status", table_name="service_tickets")
    op.drop_index("ix_service_tickets_customer_id", table_name="service_tickets")
    op.drop_index("ix_service_tickets_external_ticket_id", table_name="service_tickets")
    op.drop_table("service_tickets")
