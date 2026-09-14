from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AISuggestion(Base):
    """AI 辅助建议的版本记录；accepted 只表示人工接受，不代表已发送。"""

    __tablename__ = "ai_suggestions"
    __table_args__ = (Index("ix_ai_suggestions_customer_status", "customer_id", "status"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    profile_id: Mapped[int | None] = mapped_column(ForeignKey("customer_profiles.id", ondelete="SET NULL"), nullable=True, index=True)
    suggestion_type: Mapped[str] = mapped_column(String(30), nullable=False, default="reply")

    content_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    edited_content_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    evidence_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    evidence_level: Mapped[str] = mapped_column(String(20), nullable=False, default="normal")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft", index=True)

    model_name: Mapped[str] = mapped_column(String(100), nullable=False, default="mock-rules")
    model_version: Mapped[str] = mapped_column(String(50), nullable=False, default="1")
    prompt_version: Mapped[str] = mapped_column(String(50), nullable=False, default="reply-v1")
    decided_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
