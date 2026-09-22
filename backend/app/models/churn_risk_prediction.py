"""客户流失风险评分明细。"""

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ChurnRiskPrediction(Base):
    """保存一个批次内单个外部学生的风险结果，不复制原始特征或敏感资料。"""

    __tablename__ = "churn_risk_predictions"
    __table_args__ = (
        UniqueConstraint(
            "batch_id",
            "student_external_id",
            name="uq_churn_risk_predictions_batch_student",
        ),
        Index("ix_churn_risk_predictions_batch_rank", "batch_id", "risk_rank"),
        Index("ix_churn_risk_predictions_student_created", "student_external_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    batch_id: Mapped[int] = mapped_column(
        ForeignKey("churn_scoring_batches.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # 保存评分当时匹配到的映射，避免以后映射调整时改变历史解释。
    mapping_id: Mapped[int | None] = mapped_column(
        ForeignKey("external_student_mappings.id", ondelete="SET NULL"), nullable=True, index=True
    )
    student_external_id: Mapped[str] = mapped_column(String(100), nullable=False)
    risk_probability: Mapped[float] = mapped_column(Float, nullable=False)
    risk_level: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    predicted_churn: Mapped[bool] = mapped_column(Boolean, nullable=False)
    risk_rank: Mapped[int] = mapped_column(nullable=False)
    risk_percentile: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
