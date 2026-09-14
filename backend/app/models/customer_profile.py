from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CustomerProfile(Base):
    """客户画像的版本化草稿和确认结果；AI 只能创建草稿。"""

    __tablename__ = "customer_profiles"
    __table_args__ = (
        UniqueConstraint("customer_id", "version", name="uq_customer_profiles_customer_version"),
        Index("ix_customer_profiles_customer_status", "customer_id", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft", index=True)

    # 画像维度和证据都使用结构化 JSON，避免把生成结果压成无法审阅的一段文本。
    dimensions_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    evidence_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)

    model_name: Mapped[str] = mapped_column(String(100), nullable=False, default="mock-rules")
    model_version: Mapped[str] = mapped_column(String(50), nullable=False, default="1")
    prompt_version: Mapped[str] = mapped_column(String(50), nullable=False, default="profile-v1")

    confirmed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
