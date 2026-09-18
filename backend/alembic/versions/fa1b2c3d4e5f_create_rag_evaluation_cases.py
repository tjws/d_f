"""create independent RAG evaluation cases

Revision ID: fa1b2c3d4e5f
Revises: f9a0b1c2d3e4
"""

from alembic import op
import sqlalchemy as sa


revision = "fa1b2c3d4e5f"
down_revision = "f9a0b1c2d3e4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "rag_evaluation_cases",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("interaction_id", sa.Integer(), nullable=True),
        sa.Column("customer_id", sa.Integer(), nullable=True),
        sa.Column("run_id", sa.Integer(), nullable=True),
        sa.Column("actor_user_id", sa.Integer(), nullable=True),
        sa.Column("source_type", sa.String(length=30), nullable=False),
        sa.Column("source_id", sa.String(length=100), nullable=False),
        sa.Column("query_excerpt", sa.String(length=500), nullable=True),
        sa.Column("retrieval_mode", sa.String(length=20), nullable=True),
        sa.Column("fallback", sa.Boolean(), nullable=False),
        sa.Column("expected_document_ids", sa.JSON(), nullable=True),
        sa.Column("retrieved_document_ids", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("review_note", sa.String(length=500), nullable=True),
        sa.Column("reviewed_by", sa.Integer(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["interaction_id"], ["ai_rag_interactions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["run_id"], ["ai_workflow_runs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["reviewed_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_type", "source_id", name="uq_rag_evaluation_cases_source"),
    )
    op.create_index("ix_rag_evaluation_cases_interaction_id", "rag_evaluation_cases", ["interaction_id"], unique=False)
    op.create_index("ix_rag_evaluation_cases_customer_id", "rag_evaluation_cases", ["customer_id"], unique=False)
    op.create_index("ix_rag_evaluation_cases_run_id", "rag_evaluation_cases", ["run_id"], unique=False)
    op.create_index("ix_rag_evaluation_cases_actor_user_id", "rag_evaluation_cases", ["actor_user_id"], unique=False)
    op.create_index("ix_rag_evaluation_cases_status", "rag_evaluation_cases", ["status"], unique=False)
    op.create_index("ix_rag_evaluation_cases_reviewed_by", "rag_evaluation_cases", ["reviewed_by"], unique=False)
    op.create_index("ix_rag_evaluation_cases_status_created", "rag_evaluation_cases", ["status", "created_at"], unique=False)
    op.create_index("ix_rag_evaluation_cases_customer_created", "rag_evaluation_cases", ["customer_id", "created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_rag_evaluation_cases_customer_created", table_name="rag_evaluation_cases")
    op.drop_index("ix_rag_evaluation_cases_status_created", table_name="rag_evaluation_cases")
    op.drop_index("ix_rag_evaluation_cases_reviewed_by", table_name="rag_evaluation_cases")
    op.drop_index("ix_rag_evaluation_cases_status", table_name="rag_evaluation_cases")
    op.drop_index("ix_rag_evaluation_cases_actor_user_id", table_name="rag_evaluation_cases")
    op.drop_index("ix_rag_evaluation_cases_run_id", table_name="rag_evaluation_cases")
    op.drop_index("ix_rag_evaluation_cases_customer_id", table_name="rag_evaluation_cases")
    op.drop_index("ix_rag_evaluation_cases_interaction_id", table_name="rag_evaluation_cases")
    op.drop_table("rag_evaluation_cases")
