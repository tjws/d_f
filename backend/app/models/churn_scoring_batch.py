"""客户流失批量评分任务。"""

from datetime import datetime, timezone

from typing import Any

from sqlalchemy import DateTime, Float, ForeignKey, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ChurnScoringBatch(Base):
    """记录一次模型、输入数据和评分结果摘要，便于追溯与重复验证。"""

    __tablename__ = "churn_scoring_batches"
    __table_args__ = (
        UniqueConstraint(
            "model_artifact_sha256",
            "source_sha256",
            "source_system",
            name="uq_churn_batches_model_source_system",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="running", index=True)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    model_schema_version: Mapped[str] = mapped_column(String(50), nullable=False)
    model_artifact_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    model_version_id: Mapped[int | None] = mapped_column(
        ForeignKey("churn_model_versions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    source_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    source_sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    source_system: Mapped[str] = mapped_column(String(50), nullable=False, default="csv")
    trigger_source: Mapped[str] = mapped_column(String(20), nullable=False, default="manual")
    observation_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    decision_threshold: Mapped[float] = mapped_column(Float, nullable=False)
    medium_threshold: Mapped[float] = mapped_column(Float, nullable=False)
    row_count: Mapped[int] = mapped_column(nullable=False)
    scored_count: Mapped[int] = mapped_column(nullable=False, default=0)
    high_count: Mapped[int] = mapped_column(nullable=False, default=0)
    medium_count: Mapped[int] = mapped_column(nullable=False, default=0)
    low_count: Mapped[int] = mapped_column(nullable=False, default=0)
    error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    drift_status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="insufficient_history"
    )
    drift_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
