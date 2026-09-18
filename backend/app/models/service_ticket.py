from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ServiceTicket(Base):
    """客户服务工单；当前保存 Mock/人工录入的售后跟进事实。"""

    __tablename__ = "service_tickets"
    __table_args__ = (
        Index("ix_service_tickets_customer_status", "customer_id", "status"),
        Index("ix_service_tickets_external_ticket_id", "external_ticket_id", unique=True),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    external_ticket_id: Mapped[str] = mapped_column(String(100), nullable=False)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(50), nullable=False, default="general")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="open", index=True)
    # 工单摘要可能包含联系方式或学习情况，数据库中只保存密文。
    summary_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    raw_snapshot_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
