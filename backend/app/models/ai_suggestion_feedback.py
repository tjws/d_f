"""人工处理 AI 建议的反馈；每个 AI 目标保留一个当前最终处理结果。"""

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, ForeignKey, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AISuggestionFeedback(Base):
    __tablename__ = "ai_suggestion_feedback"
    __table_args__ = (UniqueConstraint("target_type", "target_id", name="uq_ai_suggestion_feedback_target"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    suggestion_id: Mapped[int | None] = mapped_column(ForeignKey("ai_suggestions.id", ondelete="CASCADE"), nullable=True, index=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True)
    actor_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(20), nullable=False)
    edited_content: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    # Agent 反馈只保存短分类备注，不保存聊天原文。
    note: Mapped[str | None] = mapped_column(String(300), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    target_type: Mapped[str] = mapped_column(String(30), nullable=False, default="suggestion", index=True)
    target_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
