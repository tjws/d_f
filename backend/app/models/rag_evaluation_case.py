"""可复核的 RAG 评测用例。

运行遥测是追加式事实记录；评测用例则允许管理员补充期望文档和复核结论，
因此单独建表，避免修改原始遥测后无法还原当时发生了什么。
"""

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class RAGEvaluationCase(Base):
    __tablename__ = "rag_evaluation_cases"
    __table_args__ = (
        UniqueConstraint("source_type", "source_id", name="uq_rag_evaluation_cases_source"),
        Index("ix_rag_evaluation_cases_status_created", "status", "created_at"),
        Index("ix_rag_evaluation_cases_customer_created", "customer_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    interaction_id: Mapped[int | None] = mapped_column(
        ForeignKey("ai_rag_interactions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    customer_id: Mapped[int | None] = mapped_column(
        ForeignKey("customers.id", ondelete="SET NULL"), nullable=True, index=True
    )
    run_id: Mapped[int | None] = mapped_column(
        ForeignKey("ai_workflow_runs.id", ondelete="SET NULL"), nullable=True, index=True
    )
    actor_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    # source_type/source_id 是幂等来源，例如 rag_fallback:12 或 agent_feedback:18。
    source_type: Mapped[str] = mapped_column(String(30), nullable=False)
    source_id: Mapped[str] = mapped_column(String(100), nullable=False)
    query_excerpt: Mapped[str | None] = mapped_column(String(500), nullable=True)
    retrieval_mode: Mapped[str | None] = mapped_column(String(20), nullable=True)
    fallback: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    expected_document_ids: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    retrieved_document_ids: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open", index=True)
    review_note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    reviewed_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

