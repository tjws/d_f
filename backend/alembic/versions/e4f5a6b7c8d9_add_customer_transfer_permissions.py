"""add customer transfer permissions

Revision ID: e4f5a6b7c8d9
Revises: d3e4f5a6b7c8
"""

from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa


revision = "e4f5a6b7c8d9"
down_revision = "d3e4f5a6b7c8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    permissions = sa.table(
        "role_permissions",
        sa.column("role", sa.String(length=30)),
        sa.column("module", sa.String(length=50)),
        sa.column("action", sa.String(length=50)),
        sa.column("data_scope", sa.String(length=30)),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    timestamp = datetime.now(timezone.utc)
    op.bulk_insert(permissions, [
        {"role": "admin", "module": "customers", "action": "transfer", "data_scope": "all", "created_at": timestamp, "updated_at": timestamp},
        {"role": "manager", "module": "customers", "action": "transfer", "data_scope": "organization", "created_at": timestamp, "updated_at": timestamp},
    ])


def downgrade() -> None:
    op.execute("DELETE FROM role_permissions WHERE module = 'customers' AND action = 'transfer'")
