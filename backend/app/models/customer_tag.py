from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class CustomerTag(Base):
    """客户标签的建议和人工确认记录；保留来源与证据。"""

    __tablename__ = "customer_tags"
    __table_args__ = (Index("ix_customer_tags_customer_status", "customer_id", "status"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True)
    tag_id: Mapped[int] = mapped_column(ForeignKey("tags.id", ondelete="RESTRICT"), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="ai")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="suggested", index=True)
    evidence_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    confirmed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    tag: Mapped["Tag"] = relationship("Tag")
