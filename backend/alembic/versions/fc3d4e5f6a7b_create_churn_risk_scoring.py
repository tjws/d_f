"""create churn risk scoring batches and predictions

Revision ID: fc3d4e5f6a7b
Revises: fb2c3d4e5f6a
"""

from alembic import op
import sqlalchemy as sa


revision = "fc3d4e5f6a7b"
down_revision = "fb2c3d4e5f6a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "churn_scoring_batches",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("model_name", sa.String(length=100), nullable=False),
        sa.Column("model_schema_version", sa.String(length=50), nullable=False),
        sa.Column("model_artifact_sha256", sa.String(length=64), nullable=False),
        sa.Column("source_filename", sa.String(length=255), nullable=False),
        sa.Column("source_sha256", sa.String(length=64), nullable=False),
        sa.Column("decision_threshold", sa.Float(), nullable=False),
        sa.Column("medium_threshold", sa.Float(), nullable=False),
        sa.Column("row_count", sa.Integer(), nullable=False),
        sa.Column("scored_count", sa.Integer(), nullable=False),
        sa.Column("high_count", sa.Integer(), nullable=False),
        sa.Column("medium_count", sa.Integer(), nullable=False),
        sa.Column("low_count", sa.Integer(), nullable=False),
        sa.Column("error_code", sa.String(length=80), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_churn_scoring_batches_status", "churn_scoring_batches", ["status"])
    op.create_index(
        "ix_churn_scoring_batches_source_sha256",
        "churn_scoring_batches",
        ["source_sha256"],
    )

    op.create_table(
        "churn_risk_predictions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("batch_id", sa.Integer(), nullable=False),
        sa.Column("student_external_id", sa.String(length=100), nullable=False),
        sa.Column("risk_probability", sa.Float(), nullable=False),
        sa.Column("risk_level", sa.String(length=20), nullable=False),
        sa.Column("predicted_churn", sa.Boolean(), nullable=False),
        sa.Column("risk_rank", sa.Integer(), nullable=False),
        sa.Column("risk_percentile", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["batch_id"], ["churn_scoring_batches.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "batch_id",
            "student_external_id",
            name="uq_churn_risk_predictions_batch_student",
        ),
    )
    op.create_index("ix_churn_risk_predictions_batch_id", "churn_risk_predictions", ["batch_id"])
    op.create_index("ix_churn_risk_predictions_risk_level", "churn_risk_predictions", ["risk_level"])
    op.create_index(
        "ix_churn_risk_predictions_batch_rank",
        "churn_risk_predictions",
        ["batch_id", "risk_rank"],
    )
    op.create_index(
        "ix_churn_risk_predictions_student_created",
        "churn_risk_predictions",
        ["student_external_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_churn_risk_predictions_student_created", table_name="churn_risk_predictions")
    op.drop_index("ix_churn_risk_predictions_batch_rank", table_name="churn_risk_predictions")
    op.drop_index("ix_churn_risk_predictions_risk_level", table_name="churn_risk_predictions")
    op.drop_index("ix_churn_risk_predictions_batch_id", table_name="churn_risk_predictions")
    op.drop_table("churn_risk_predictions")
    op.drop_index("ix_churn_scoring_batches_source_sha256", table_name="churn_scoring_batches")
    op.drop_index("ix_churn_scoring_batches_status", table_name="churn_scoring_batches")
    op.drop_table("churn_scoring_batches")

