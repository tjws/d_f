from datetime import datetime, timezone

from sqlalchemy import DateTime, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class KnowledgeDocument(Base):
    """可发布的业务知识文档；文档正文拆分后保存到 knowledge_chunks。"""

    __tablename__ = "knowledge_documents"
    __table_args__ = (
        Index("ix_knowledge_documents_status_category", "status", "category"),
        Index("ix_knowledge_documents_slug", "slug", unique=True),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(120), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False, default="general")
    source: Mapped[str] = mapped_column(String(100), nullable=False, default="admin")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft", index=True)
    created_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    published_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # 向量索引是可重建的派生数据，状态失败不应阻断文档发布或关键词检索。
    vector_index_status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", index=True)
    vector_index_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    vector_index_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    vector_indexed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    vector_content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    vector_embedding_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    chunks = relationship("KnowledgeChunk", back_populates="document", cascade="all, delete-orphan", order_by="KnowledgeChunk.chunk_index")
