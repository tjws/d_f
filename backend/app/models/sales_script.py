from datetime import datetime, timezone

from sqlalchemy import DateTime, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SalesScript(Base):
    """经过审核的销售话术；只有 published 版本进入 AI 上下文。"""

    __tablename__ = "sales_scripts"
    __table_args__ = (Index("ix_sales_scripts_status_scene", "status", "scene"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    scene: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    customer_stage: Mapped[str | None] = mapped_column(String(30), nullable=True, index=True)
    objection_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    tone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="draft", index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_by: Mapped[int | None] = mapped_column(nullable=True, index=True)
    approved_by: Mapped[int | None] = mapped_column(nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
