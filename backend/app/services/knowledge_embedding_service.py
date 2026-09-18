"""知识分片向量化与 Qdrant 写入服务。"""

from __future__ import annotations

import hashlib

from qdrant_client.http import models
from sqlalchemy.orm import Session

from app.ai.embeddings.factory import get_embedding_provider
from app.ai.providers.base import EmbeddingProvider
from app.dao.knowledge_chunk_dao import KnowledgeChunkDAO
from app.knowledge.qdrant_store import upsert_chunks


chunk_dao = KnowledgeChunkDAO()


def index_published_knowledge(
    db: Session,
    document_id: int | None = None,
    provider: EmbeddingProvider | None = None,
    client=None,
) -> int:
    """将已发布分片写入 Qdrant；重复执行使用同一 chunk id 覆盖，不产生重复点。"""
    rows = chunk_dao.list_published(db)
    if document_id is not None:
        rows = [row for row in rows if row[1].id == document_id]
    if not rows:
        return 0
    embedding_provider = provider or get_embedding_provider()
    texts = [chunk.content for chunk, _document in rows]
    vectors = embedding_provider.embed(texts)
    if len(vectors) != len(rows):
        raise ValueError("embedding count does not match knowledge chunks")
    points: list[models.PointStruct] = []
    for (chunk, document), vector in zip(rows, vectors, strict=True):
        if not vector:
            raise ValueError(f"empty embedding for chunk {chunk.id}")
        points.append(
            models.PointStruct(
                id=chunk.id,
                vector=vector,
                payload={
                    "chunk_id": chunk.id,
                    "document_id": document.id,
                    "document_slug": document.slug,
                    "title": document.title,
                    "category": document.category,
                    "source": document.source,
                    "status": document.status,
                    "version": document.version,
                    "content": chunk.content,
                    "content_hash": hashlib.sha256(chunk.content.encode("utf-8")).hexdigest(),
                    "embedding_model": embedding_provider.model_name,
                },
            )
        )
    upsert_chunks(points, client=client)
    return len(points)


def content_hash_for_chunks(rows: list[tuple[object, object]]) -> str:
    """用分片正文计算稳定 hash，作为是否需要重新 Embedding 的依据。"""
    content = "\n\n".join(str(chunk.content) for chunk, _document in rows)
    return hashlib.sha256(content.encode("utf-8")).hexdigest()
