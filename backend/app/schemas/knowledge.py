from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


KnowledgeStatus = Literal["draft", "published", "disabled"]
KnowledgeIndexStatus = Literal["pending", "indexing", "ready", "failed", "disabled"]
KnowledgeRetrievalMode = Literal["keyword", "vector", "mixed"]


class KnowledgeSearchItem(BaseModel):
    """前端可展示的单条知识片段，不返回内部文档全文。"""

    document_id: str
    chunk_id: int | None = None
    title: str
    snippet: str
    score: float


class KnowledgeSearchRead(BaseModel):
    """知识检索结果及“是否足够支持回答”的策略判断。"""

    query: str
    matched: bool
    retrieval_mode: KnowledgeRetrievalMode
    threshold: float
    fallback_message: str | None = None
    items: list[KnowledgeSearchItem] = Field(default_factory=list)


class KnowledgeDocumentCreate(BaseModel):
    slug: str = Field(min_length=2, max_length=120, pattern=r"^[a-zA-Z0-9_-]+$")
    title: str = Field(min_length=1, max_length=200)
    category: str = Field(default="general", min_length=1, max_length=50)
    source: str = Field(default="admin", max_length=100)
    content: str = Field(min_length=10, max_length=50000)


class KnowledgeDocumentUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    category: str | None = Field(default=None, min_length=1, max_length=50)
    content: str | None = Field(default=None, min_length=10, max_length=50000)
    status: KnowledgeStatus | None = None


class KnowledgeChunkRead(BaseModel):
    id: int
    chunk_index: int
    content: str


class KnowledgeDocumentRead(BaseModel):
    id: int
    slug: str
    title: str
    category: str
    source: str
    version: int
    status: KnowledgeStatus
    created_by: int | None
    published_by: int | None
    published_at: datetime | None
    created_at: datetime
    updated_at: datetime
    vector_index_status: KnowledgeIndexStatus
    vector_index_error: str | None
    vector_index_attempts: int
    vector_indexed_at: datetime | None
    vector_content_hash: str | None
    vector_embedding_model: str | None
    chunks: list[KnowledgeChunkRead] = Field(default_factory=list)
