"""extend churn risk with mapping, interventions and model governance

Revision ID: fd4e5f6a7b8c
Revises: fc3d4e5f6a7b
"""

from alembic import op
import sqlalchemy as sa


revision = "fd4e5f6a7b8c"
down_revision = "fc3d4e5f6a7b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "external_student_mappings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("source_system", sa.String(length=50), nullable=False),
        sa.Column("external_student_id", sa.String(length=100), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source_system",
            "external_student_id",
            name="uq_external_student_mappings_source_student",
        ),
    )
    op.create_index("ix_external_student_mappings_source_system", "external_student_mappings", ["source_system"])
    op.create_index("ix_external_student_mappings_external_student_id", "external_student_mappings", ["external_student_id"])
    op.create_index("ix_external_student_mappings_student_id", "external_student_mappings", ["student_id"])
    op.create_index("ix_external_student_mappings_created_by", "external_student_mappings", ["created_by"])

    op.create_table(
        "churn_model_versions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("version", sa.String(length=80), nullable=False),
        sa.Column("model_name", sa.String(length=100), nullable=False),
        sa.Column("schema_version", sa.String(length=50), nullable=False),
        sa.Column("artifact_filename", sa.String(length=255), nullable=False),
        sa.Column("artifact_sha256", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("decision_threshold", sa.Float(), nullable=False),
        sa.Column("medium_threshold", sa.Float(), nullable=False),
        sa.Column("metrics_json", sa.JSON(), nullable=False),
        sa.Column("approved_by", sa.Integer(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["approved_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("artifact_sha256"),
        sa.UniqueConstraint("version"),
    )
    op.create_index("ix_churn_model_versions_status", "churn_model_versions", ["status"])

    with op.batch_alter_table("churn_scoring_batches") as batch_op:
        batch_op.add_column(sa.Column("model_version_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("source_system", sa.String(length=50), nullable=False, server_default="csv"))
        batch_op.add_column(sa.Column("trigger_source", sa.String(length=20), nullable=False, server_default="manual"))
        batch_op.add_column(sa.Column("observation_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("drift_status", sa.String(length=30), nullable=False, server_default="insufficient_history"))
        batch_op.add_column(sa.Column("drift_json", sa.JSON(), nullable=False, server_default="{}"))
        batch_op.create_foreign_key(
            "fk_churn_batches_model_version",
            "churn_model_versions",
            ["model_version_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index("ix_churn_scoring_batches_model_version_id", ["model_version_id"])
        batch_op.create_unique_constraint(
            "uq_churn_batches_model_source_system",
            ["model_artifact_sha256", "source_sha256", "source_system"],
        )

    with op.batch_alter_table("churn_risk_predictions") as batch_op:
        batch_op.add_column(sa.Column("mapping_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_churn_predictions_mapping",
            "external_student_mappings",
            ["mapping_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index("ix_churn_risk_predictions_mapping_id", ["mapping_id"])

    op.create_table(
        "churn_risk_interventions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("prediction_id", sa.Integer(), nullable=False),
        sa.Column("customer_id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("actor_user_id", sa.Integer(), nullable=True),
        sa.Column("schedule_id", sa.Integer(), nullable=True),
        sa.Column("action_type", sa.String(length=30), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("outcome", sa.String(length=30), nullable=True),
        sa.Column("note_encrypted", sa.Text(), nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["prediction_id"], ["churn_risk_predictions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["schedule_id"], ["schedules.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("prediction_id", name="uq_churn_interventions_prediction"),
    )
    for column in ("prediction_id", "customer_id", "student_id", "actor_user_id", "schedule_id", "status", "outcome", "due_at"):
        op.create_index(f"ix_churn_risk_interventions_{column}", "churn_risk_interventions", [column])


def downgrade() -> None:
    op.drop_table("churn_risk_interventions")
    with op.batch_alter_table("churn_risk_predictions") as batch_op:
        batch_op.drop_index("ix_churn_risk_predictions_mapping_id")
        batch_op.drop_constraint("fk_churn_predictions_mapping", type_="foreignkey")
        batch_op.drop_column("mapping_id")
    with op.batch_alter_table("churn_scoring_batches") as batch_op:
        batch_op.drop_constraint("uq_churn_batches_model_source_system", type_="unique")
        batch_op.drop_index("ix_churn_scoring_batches_model_version_id")
        batch_op.drop_constraint("fk_churn_batches_model_version", type_="foreignkey")
        for column in ("drift_json", "drift_status", "observation_at", "trigger_source", "source_system", "model_version_id"):
            batch_op.drop_column(column)
    op.drop_table("churn_model_versions")
    op.drop_table("external_student_mappings")
