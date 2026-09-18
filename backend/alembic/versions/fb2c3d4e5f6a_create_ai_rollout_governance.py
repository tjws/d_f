"""create AI rollout membership and daily report tables

Revision ID: fb2c3d4e5f6a
Revises: fa1b2c3d4e5f
"""

from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa


revision = "fb2c3d4e5f6a"
down_revision = "fa1b2c3d4e5f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ai_rollout_memberships",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("segment", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("added_by", sa.Integer(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["added_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_ai_rollout_memberships_user"),
    )
    op.create_index("ix_ai_rollout_memberships_user_id", "ai_rollout_memberships", ["user_id"], unique=False)
    op.create_index("ix_ai_rollout_memberships_status", "ai_rollout_memberships", ["status"], unique=False)
    op.create_index("ix_ai_rollout_memberships_added_by", "ai_rollout_memberships", ["added_by"], unique=False)
    op.create_index("ix_ai_rollout_memberships_status_started", "ai_rollout_memberships", ["status", "started_at"], unique=False)

    op.create_table(
        "ai_rollout_daily_reports",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("report_date", sa.Date(), nullable=False),
        sa.Column("cohort", sa.String(length=30), nullable=False),
        sa.Column("metrics_json", sa.JSON(), nullable=False),
        sa.Column("generated_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["generated_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("report_date", "cohort", name="uq_ai_rollout_daily_reports_date_cohort"),
    )
    op.create_index("ix_ai_rollout_daily_reports_report_date", "ai_rollout_daily_reports", ["report_date"], unique=False)

    settings = sa.table(
        "system_settings",
        sa.column("key", sa.String),
        sa.column("value_json", sa.JSON),
        sa.column("scope_type", sa.String),
        sa.column("scope_id", sa.Integer),
        sa.column("description", sa.String),
        sa.column("updated_at", sa.DateTime),
    )
    timestamp = datetime.now(timezone.utc)
    op.bulk_insert(settings, [{
        "key": "ai_rollout_mode",
        "value_json": "all",
        "scope_type": "global",
        "scope_id": None,
        "description": "AI 综合 Agent 灰度模式：all 全量，pilot 仅 active 灰度名单。",
        "updated_at": timestamp,
    }])


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM system_settings WHERE key = 'ai_rollout_mode' AND scope_type = 'global' AND scope_id IS NULL"))
    op.drop_index("ix_ai_rollout_daily_reports_report_date", table_name="ai_rollout_daily_reports")
    op.drop_table("ai_rollout_daily_reports")
    op.drop_index("ix_ai_rollout_memberships_status_started", table_name="ai_rollout_memberships")
    op.drop_index("ix_ai_rollout_memberships_added_by", table_name="ai_rollout_memberships")
    op.drop_index("ix_ai_rollout_memberships_status", table_name="ai_rollout_memberships")
    op.drop_index("ix_ai_rollout_memberships_user_id", table_name="ai_rollout_memberships")
    op.drop_table("ai_rollout_memberships")
