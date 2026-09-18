"""add RAG telemetry, Agent feedback notes and the comprehensive kill switch

Revision ID: f9a0b1c2d3e4
Revises: f8c9d0e1f2a3
"""

from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa


revision = "f9a0b1c2d3e4"
down_revision = "f8c9d0e1f2a3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "ai_suggestion_feedback",
        sa.Column("note", sa.String(length=300), nullable=True),
    )
    op.create_table(
        "ai_rag_interactions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("customer_id", sa.Integer(), nullable=True),
        sa.Column("actor_user_id", sa.Integer(), nullable=True),
        sa.Column("run_id", sa.Integer(), nullable=True),
        sa.Column("suggestion_id", sa.Integer(), nullable=True),
        sa.Column("entrypoint", sa.String(length=30), nullable=False),
        sa.Column("query_excerpt", sa.String(length=240), nullable=True),
        sa.Column("retrieval_mode", sa.String(length=20), nullable=False),
        sa.Column("matched", sa.Boolean(), nullable=False),
        sa.Column("fallback", sa.Boolean(), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["run_id"], ["ai_workflow_runs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["suggestion_id"], ["ai_suggestions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ai_rag_interactions_customer_id", "ai_rag_interactions", ["customer_id"], unique=False)
    op.create_index("ix_ai_rag_interactions_actor_user_id", "ai_rag_interactions", ["actor_user_id"], unique=False)
    op.create_index("ix_ai_rag_interactions_created_at", "ai_rag_interactions", ["created_at"], unique=False)
    op.create_index("ix_ai_rag_interactions_entrypoint_created", "ai_rag_interactions", ["entrypoint", "created_at"], unique=False)
    op.create_index("ix_ai_rag_interactions_run_id", "ai_rag_interactions", ["run_id"], unique=False)
    settings = sa.table(
        "system_settings",
        sa.column("key", sa.String),
        sa.column("value_json", sa.JSON),
        sa.column("scope_type", sa.String),
        sa.column("scope_id", sa.Integer),
        sa.column("description", sa.String),
        sa.column("updated_at", sa.DateTime),
    )
    op.bulk_insert(settings, [
        {
            "key": "comprehensive_agent_enabled",
            "value_json": True,
            "scope_type": "global",
            "scope_id": None,
            "description": "综合 Agent 全局开关；关闭后退回普通回复建议，不影响人工发送边界。",
            "updated_at": datetime.now(timezone.utc),
        }
    ])


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM system_settings WHERE key = 'comprehensive_agent_enabled' AND scope_type = 'global' AND scope_id IS NULL"))
    op.drop_index("ix_ai_rag_interactions_run_id", table_name="ai_rag_interactions")
    op.drop_index("ix_ai_rag_interactions_entrypoint_created", table_name="ai_rag_interactions")
    op.drop_index("ix_ai_rag_interactions_created_at", table_name="ai_rag_interactions")
    op.drop_index("ix_ai_rag_interactions_actor_user_id", table_name="ai_rag_interactions")
    op.drop_index("ix_ai_rag_interactions_customer_id", table_name="ai_rag_interactions")
    op.drop_table("ai_rag_interactions")
    op.drop_column("ai_suggestion_feedback", "note")
