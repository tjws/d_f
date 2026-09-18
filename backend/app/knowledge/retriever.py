from dataclasses import dataclass
from functools import lru_cache
import os
from pathlib import Path
import re

from sqlalchemy.orm import Session

from app.dao.knowledge_chunk_dao import KnowledgeChunkDAO


KNOWLEDGE_ROOT = Path(__file__).resolve().parents[2] / "data" / "knowledge"


@dataclass(frozen=True)
class KnowledgeDocument:
    """召回给 AI 的最小资料片段，不携带客户隐私。"""

    document_id: str
    title: str
    content: str
    score: float
    chunk_id: int | None = None


def _tokens(text: str) -> set[str]:
    # 中文按单字切分，英文按词切分；后续可替换专业分词器。
    return set(re.findall(r"[\u4e00-\u9fff]|[a-zA-Z0-9]+", text.lower()))


@lru_cache(maxsize=1)
def _load_documents() -> tuple[tuple[str, str, str], ...]:
    documents: list[tuple[str, str, str]] = []
    if not KNOWLEDGE_ROOT.exists():
        return ()
    for path in sorted(KNOWLEDGE_ROOT.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        title = next((line.lstrip("# ").strip() for line in text.splitlines() if line.startswith("#")), path.stem)
        documents.append((path.stem, title, text[:6000]))
    return tuple(documents)


def search_knowledge(query: str, limit: int = 5, db: Session | None = None, use_vector: bool | None = None) -> list[KnowledgeDocument]:
    """按配置执行 Qdrant 向量召回，再用关键词结果补足；异常时安全降级。"""
    if not query.strip() or limit <= 0:
        return []
    query_tokens = _tokens(query)
    ranked: list[KnowledgeDocument] = []
    vector_enabled = use_vector if use_vector is not None else os.getenv("RAG_VECTOR_ENABLED", "0").strip() == "1"
    if vector_enabled:
        try:
            from app.ai.embeddings.factory import get_embedding_provider
            from app.knowledge.qdrant_store import search_vectors
            from qdrant_client.http import models

            provider = get_embedding_provider()
            query_vector = provider.embed([query])[0]
            points = search_vectors(
                query_vector,
                limit=limit,
                query_filter=models.Filter(
                    must=[models.FieldCondition(key="status", match=models.MatchValue(value="published"))]
                ),
            )
            for point in points:
                payload = point.payload or {}
                if not isinstance(payload, dict) or not payload.get("document_slug"):
                    continue
                ranked.append(
                    KnowledgeDocument(
                        str(payload["document_slug"]),
                        str(payload.get("title", payload["document_slug"])),
                        str(payload.get("content", "")),
                        100.0 + float(point.score),
                        int(payload["chunk_id"]) if payload.get("chunk_id") is not None else None,
                    )
                )
        except Exception:
            # Qdrant 或 Embedding 暂不可用时，继续使用可解释的本地关键词检索。
            ranked = []
    if db is not None:
        for chunk, document in KnowledgeChunkDAO().list_published(db):
            score = len(query_tokens & _tokens(f"{document.title}\n{chunk.content}\n{chunk.keywords or ''}"))
            if score:
                ranked.append(KnowledgeDocument(document.slug, document.title, chunk.content, score, chunk.id))
    for document_id, title, content in _load_documents():
        score = len(query_tokens & _tokens(f"{title}\n{content}"))
        if score:
            # 数据库文档与静态资料使用同一 slug 时，优先数据库中的已发布版本。
            if not any(item.document_id == document_id for item in ranked):
                ranked.append(KnowledgeDocument(document_id, title, content, score))
    ranked.sort(key=lambda item: (-item.score, item.document_id))
    return ranked[:limit]
