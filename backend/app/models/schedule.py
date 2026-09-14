from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Schedule(Base):
    """人工确认后的跟进日程；AI 建议确认前不会写入本表。"""

    __tablename__ = "schedules"
    __table_args__ = (Index("ix_schedules_customer_status", "customer_id", "status"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    suggestion_id: Mapped[int | None] = mapped_column(ForeignKey("ai_suggestions.id", ondelete="SET NULL"), nullable=True, unique=True, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    priority: Mapped[str] = mapped_column(String(20), nullable=False, default="normal")
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="ai")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="confirmed", index=True)
    evidence_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    confirmed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    wecom_calendar_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
