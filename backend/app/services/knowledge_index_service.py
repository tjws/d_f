"""知识库向量索引生命周期：状态记录、幂等跳过与任务投递。"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone

from app.dao.knowledge_document_dao import KnowledgeDocumentDAO
from app.db.session import SessionLocal
from app.knowledge.qdrant_store import delete_document_vectors
from app.ai.embeddings.factory import get_embedding_provider
from app.services.knowledge_embedding_service import content_hash_for_chunks, index_published_knowledge


logger = logging.getLogger("k12.knowledge")
document_dao = KnowledgeDocumentDAO()


def index_one_document(document_id: int, *, force: bool = False) -> int:
    """在独立数据库会话中索引单份已发布文档，并持久化结果状态。"""
    with SessionLocal() as db:
        document = document_dao.get_by_id(db, document_id)
        if document is None:
            return 0
        if document.status != "published":
            document.vector_index_status = "disabled"
            document.vector_index_error = None
            db.commit()
            return 0
        rows = [(chunk, document) for chunk in document.chunks]
        content_hash = content_hash_for_chunks(rows)
        provider_name = get_embedding_provider().model_name
        if not force and document.vector_index_status == "ready" and document.vector_content_hash == content_hash and document.vector_embedding_model == provider_name:
            return 0
        document.vector_index_status = "indexing"
        document.vector_index_attempts += 1
        document.vector_index_error = None
        db.commit()
        try:
            delete_document_vectors(document.id)
            indexed = index_published_knowledge(db, document_id=document.id)
            document.vector_index_status = "ready"
            document.vector_index_error = None
            document.vector_content_hash = content_hash
            document.vector_embedding_model = provider_name
            document.vector_indexed_at = datetime.now(timezone.utc)
            db.commit()
            logger.info("knowledge_index_succeeded", extra={"event": "knowledge_index_succeeded", "document_id": document.id, "indexed": indexed})
            return len(document.chunks)
        except Exception as exc:
            document.vector_index_status = "failed"
            document.vector_index_error = str(exc)[:500]
            db.commit()
            logger.exception("knowledge_index_failed", extra={"event": "knowledge_index_failed", "document_id": document.id})
            raise


def reindex_all_published(*, force: bool = True) -> int:
    """管理后台手动重建所有已发布文档，并复用单文档状态记录。"""
    with SessionLocal() as db:
        document_ids = [item.id for item in document_dao.list_all(db) if item.status == "published"]
    return sum(index_one_document(document_id, force=force) for document_id in document_ids)


def enqueue_knowledge_index(document_id: int) -> None:
    """发布事务提交后投递任务；本地默认手动，Compose 显式启用 queue。"""
    mode = os.getenv("KNOWLEDGE_INDEX_EXECUTION_MODE", "manual").strip().lower()
    if mode == "manual":
        return
    if mode == "sync":
        try:
            index_one_document(document_id)
        except Exception:
            logger.exception("knowledge_index_sync_failed", extra={"event": "knowledge_index_sync_failed", "document_id": document_id})
        return
    if mode != "queue":
        logger.warning("knowledge_index_mode_unsupported", extra={"event": "knowledge_index_mode_unsupported", "mode": mode})
        return
    try:
        from app.workers.knowledge_tasks import index_knowledge_document_task

        index_knowledge_document_task.send(document_id)
    except Exception:
        logger.exception("knowledge_index_enqueue_failed", extra={"event": "knowledge_index_enqueue_failed", "document_id": document_id})
