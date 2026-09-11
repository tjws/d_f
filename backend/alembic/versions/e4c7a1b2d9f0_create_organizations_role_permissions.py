"""create organizations and role permissions

Revision ID: e4c7a1b2d9f0
Revises: d9be7dac6f94
Create Date: 2026-09-11

"""
from datetime import datetime, timezone
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e4c7a1b2d9f0"
down_revision: Union[str, None] = "d9be7dac6f94"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """创建组织树、权限配置，并写入三种固定角色的基础权限。"""

    op.create_table(
        "organizations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("parent_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("type", sa.String(length=30), nullable=False),
        sa.Column("path", sa.String(length=500), nullable=True),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default="active",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["parent_id"],
            ["organizations.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_organizations_parent_id",
        "organizations",
        ["parent_id"],
        unique=False,
    )
    op.create_index(
        "ix_organizations_status",
        "organizations",
        ["status"],
        unique=False,
    )

    op.create_table(
        "role_permissions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("role", sa.String(length=30), nullable=False),
        sa.Column("module", sa.String(length=50), nullable=False),
        sa.Column("action", sa.String(length=50), nullable=False),
        sa.Column("data_scope", sa.String(length=30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "role",
            "module",
            "action",
            name="uq_role_permissions_role_module_action",
        ),
    )
    op.create_index(
        "ix_role_permissions_role",
        "role_permissions",
        ["role"],
        unique=False,
    )
    op.create_index(
        "ix_role_permissions_module",
        "role_permissions",
        ["module"],
        unique=False,
    )

    role_permissions = sa.table(
        "role_permissions",
        sa.column("role", sa.String(length=30)),
        sa.column("module", sa.String(length=50)),
        sa.column("action", sa.String(length=50)),
        sa.column("data_scope", sa.String(length=30)),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )

    # 这些种子数据只描述权限边界，当前 API 仍使用原有固定角色判断。
    permission_rows = [
        {"role": "admin", "module": "users", "action": "read", "data_scope": "all"},
        {"role": "admin", "module": "users", "action": "role_update", "data_scope": "all"},
        {"role": "admin", "module": "customers", "action": "read", "data_scope": "all"},
        {"role": "admin", "module": "customers", "action": "create", "data_scope": "all"},
        {"role": "admin", "module": "customers", "action": "update", "data_scope": "all"},
        {"role": "admin", "module": "customers", "action": "delete", "data_scope": "all"},
        {"role": "admin", "module": "audit_logs", "action": "read", "data_scope": "all"},
        {"role": "manager", "module": "users", "action": "read", "data_scope": "team"},
        {"role": "manager", "module": "customers", "action": "read", "data_scope": "organization"},
        {"role": "manager", "module": "customers", "action": "create", "data_scope": "organization"},
        {"role": "manager", "module": "customers", "action": "update", "data_scope": "organization"},
        {"role": "manager", "module": "customers", "action": "delete", "data_scope": "organization"},
        {"role": "sales", "module": "customers", "action": "read", "data_scope": "own"},
        {"role": "sales", "module": "customers", "action": "create", "data_scope": "own"},
        {"role": "sales", "module": "customers", "action": "update", "data_scope": "own"},
        {"role": "sales", "module": "customers", "action": "delete", "data_scope": "own"},
    ]
    seed_timestamp = datetime.now(timezone.utc)
    for row in permission_rows:
        row["created_at"] = seed_timestamp
        row["updated_at"] = seed_timestamp

    op.bulk_insert(role_permissions, permission_rows)


def downgrade() -> None:
    """删除权限配置和组织树。"""

    op.drop_index("ix_role_permissions_module", table_name="role_permissions")
    op.drop_index("ix_role_permissions_role", table_name="role_permissions")
    op.drop_table("role_permissions")

    op.drop_index("ix_organizations_status", table_name="organizations")
    op.drop_index("ix_organizations_parent_id", table_name="organizations")
    op.drop_table("organizations")
