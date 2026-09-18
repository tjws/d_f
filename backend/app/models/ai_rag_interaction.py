"""RAG 检索遥测记录。

只保存脱敏且截断的查询摘要、检索结果和入口信息，供治理看板统计兜底率；
不把完整聊天正文、模型提示词或 API Key 写入这张表。
"""

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AIRagInteraction(Base):
    __tablename__ = "ai_rag_interactions"
    __table_args__ = (
        Index("ix_ai_rag_interactions_created_at", "created_at"),
        Index("ix_ai_rag_interactions_entrypoint_created", "entrypoint", "created_at"),
        Index("ix_ai_rag_interactions_run_id", "run_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    customer_id: Mapped[int | None] = mapped_column(
        ForeignKey("customers.id", ondelete="CASCADE"), nullable=True, index=True
    )
    actor_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    run_id: Mapped[int | None] = mapped_column(
        ForeignKey("ai_workflow_runs.id", ondelete="SET NULL"), nullable=True
    )
    suggestion_id: Mapped[int | None] = mapped_column(
        ForeignKey("ai_suggestions.id", ondelete="SET NULL"), nullable=True
    )
    # 入口用于区分普通回复上下文、综合 Agent 和未来的人工搜索。
    entrypoint: Mapped[str] = mapped_column(String(30), nullable=False)
    query_excerpt: Mapped[str | None] = mapped_column(String(240), nullable=True)
    retrieval_mode: Mapped[str] = mapped_column(String(20), nullable=False)
    matched: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    fallback: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    metadata_json: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
