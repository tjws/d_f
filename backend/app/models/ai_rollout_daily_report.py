"""AI 灰度每日指标快照。"""

from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import Date, DateTime, ForeignKey, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AIRolloutDailyReport(Base):
    __tablename__ = "ai_rollout_daily_reports"
    __table_args__ = (
        UniqueConstraint("report_date", "cohort", name="uq_ai_rollout_daily_reports_date_cohort"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    report_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    cohort: Mapped[str] = mapped_column(String(30), nullable=False, default="pilot")
    metrics_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    generated_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

