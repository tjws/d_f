"""add organization management permissions

Revision ID: 8c2e6a1f4b90
Revises: 5fdc4354d757
Create Date: 2026-09-11

"""
from datetime import datetime, timezone
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "8c2e6a1f4b90"
down_revision: Union[str, None] = "5fdc4354d757"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """增加组织管理和用户组织分配权限。"""

    role_permissions = sa.table(
        "role_permissions",
        sa.column("role", sa.String(length=30)),
        sa.column("module", sa.String(length=50)),
        sa.column("action", sa.String(length=50)),
        sa.column("data_scope", sa.String(length=30)),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    seed_timestamp = datetime.now(timezone.utc)

    op.bulk_insert(
        role_permissions,
        [
            {
                "role": "admin",
                "module": "organizations",
                "action": "read",
                "data_scope": "all",
                "created_at": seed_timestamp,
                "updated_at": seed_timestamp,
            },
            {
                "role": "admin",
                "module": "organizations",
                "action": "create",
                "data_scope": "all",
                "created_at": seed_timestamp,
                "updated_at": seed_timestamp,
            },
            {
                "role": "admin",
                "module": "users",
                "action": "organization_assign",
                "data_scope": "all",
                "created_at": seed_timestamp,
                "updated_at": seed_timestamp,
            },
        ],
    )


def downgrade() -> None:
    """移除本迁移增加的权限。"""

    op.execute(
        sa.text(
            """
            DELETE FROM role_permissions
            WHERE (role = 'admin' AND module = 'organizations'
                   AND action IN ('read', 'create'))
               OR (role = 'admin' AND module = 'users'
                   AND action = 'organization_assign')
            """
        )
    )
