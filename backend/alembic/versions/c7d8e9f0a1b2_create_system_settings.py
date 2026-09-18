"""create system settings

Revision ID: c7d8e9f0a1b2
Revises: b6c7d8e9f0a1
"""

from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa


revision = "c7d8e9f0a1b2"
down_revision = "b6c7d8e9f0a1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "system_settings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("key", sa.String(length=100), nullable=False),
        sa.Column("value_json", sa.JSON(), nullable=False),
        sa.Column("scope_type", sa.String(length=30), nullable=False),
        sa.Column("scope_id", sa.Integer(), nullable=True),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key", "scope_type", "scope_id", name="uq_system_settings_key_scope"),
    )
    op.create_index("ix_system_settings_key", "system_settings", ["key"], unique=False)
    op.create_index("ix_system_settings_updated_by", "system_settings", ["updated_by"], unique=False)
    timestamp = datetime.now(timezone.utc)
    settings = sa.table("system_settings", sa.column("key", sa.String), sa.column("value_json", sa.JSON), sa.column("scope_type", sa.String), sa.column("scope_id", sa.Integer), sa.column("description", sa.String), sa.column("updated_at", sa.DateTime))
    op.bulk_insert(settings, [
        {"key": "ai_daily_bailian_request_limit", "value_json": 20, "scope_type": "global", "scope_id": None, "description": "单个用户每日百炼调用上限；provider 仍由环境变量控制。", "updated_at": timestamp},
        {"key": "knowledge_max_results", "value_json": 4, "scope_type": "global", "scope_id": None, "description": "AI 上下文最多带入的本地知识条目数。", "updated_at": timestamp},
        {"key": "default_follow_up_days", "value_json": 3, "scope_type": "global", "scope_id": None, "description": "默认跟进提醒天数。", "updated_at": timestamp},
    ])


def downgrade() -> None:
    op.drop_index("ix_system_settings_updated_by", table_name="system_settings")
    op.drop_index("ix_system_settings_key", table_name="system_settings")
    op.drop_table("system_settings")
