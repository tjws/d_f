from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.dao.knowledge_chunk_dao import KnowledgeChunkDAO
from app.dao.knowledge_document_dao import KnowledgeDocumentDAO
from app.models.knowledge_chunk import KnowledgeChunk
from app.models.knowledge_document import KnowledgeDocument
from app.models.user import User
from app.schemas.knowledge import KnowledgeDocumentCreate, KnowledgeDocumentUpdate
from app.services.audit_log_service import append_audit_log


document_dao = KnowledgeDocumentDAO()
chunk_dao = KnowledgeChunkDAO()


def _split_content(content: str, max_chars: int = 900) -> list[str]:
    """按段落切分并限制单片长度，保持本地 RAG 结果易读。"""
    paragraphs = [item.strip() for item in content.split("\n\n") if item.strip()]
    chunks: list[str] = []
    for paragraph in paragraphs:
        if len(paragraph) <= max_chars:
            chunks.append(paragraph)
            continue
        chunks.extend(paragraph[index:index + max_chars] for index in range(0, len(paragraph), max_chars))
    return chunks


def to_document_read(document: KnowledgeDocument) -> dict[str, object]:
    return {
        "id": document.id,
        "slug": document.slug,
        "title": document.title,
        "category": document.category,
        "source": document.source,
        "version": document.version,
        "status": document.status,
        "created_by": document.created_by,
        "published_by": document.published_by,
        "published_at": document.published_at,
        "created_at": document.created_at,
        "updated_at": document.updated_at,
        "vector_index_status": document.vector_index_status,
        "vector_index_error": document.vector_index_error,
        "vector_index_attempts": document.vector_index_attempts,
        "vector_indexed_at": document.vector_indexed_at,
        "vector_content_hash": document.vector_content_hash,
        "vector_embedding_model": document.vector_embedding_model,
        "chunks": [{"id": chunk.id, "chunk_index": chunk.chunk_index, "content": chunk.content} for chunk in document.chunks],
    }


def list_documents(db: Session) -> list[KnowledgeDocument]:
    return document_dao.list_all(db)


def create_document(db: Session, actor: User, payload: KnowledgeDocumentCreate) -> KnowledgeDocument:
    if document_dao.get_by_slug(db, payload.slug) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="知识文档标识已存在")
    document = KnowledgeDocument(slug=payload.slug, title=payload.title, category=payload.category, source=payload.source, created_by=actor.id)
    document.chunks = [KnowledgeChunk(chunk_index=index, content=content) for index, content in enumerate(_split_content(payload.content))]
    document_dao.add(db, document)
    append_audit_log(db, actor, "knowledge_document.created", "knowledge_document", payload.slug, {"title": payload.title, "status": "draft"})
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="知识文档标识已存在") from None
    db.refresh(document)
    return document_dao.get_by_id(db, document.id) or document


def update_document(db: Session, document_id: int, actor: User, payload: KnowledgeDocumentUpdate) -> KnowledgeDocument:
    document = document_dao.get_by_id(db, document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="知识文档不存在")
    was_published = document.status == "published"
    if payload.status is not None:
        allowed = {"draft": {"published", "disabled"}, "published": {"disabled", "draft"}, "disabled": {"draft"}}
        if payload.status != document.status and payload.status not in allowed.get(document.status, set()):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="知识文档状态流转不合法")
    content_changed = payload.content is not None and payload.content.strip() != "\n\n".join(chunk.content for chunk in document.chunks)
    if payload.title is not None:
        document.title = payload.title
    if payload.category is not None:
        document.category = payload.category
    if content_changed:
        document.chunks.clear()
        document.chunks.extend(KnowledgeChunk(chunk_index=index, content=content) for index, content in enumerate(_split_content(payload.content or "")))
        document.version += 1
        document.vector_index_status = "pending"
        document.vector_index_error = None
        document.vector_content_hash = None
        document.vector_indexed_at = None
        if document.status == "published":
            document.status = "draft"
            document.published_by = None
            document.published_at = None
    if payload.status is not None and payload.status != document.status:
        document.status = payload.status
        if payload.status == "published":
            document.published_by = actor.id
            document.published_at = datetime.now(timezone.utc)
            document.vector_index_status = "pending"
            document.vector_index_error = None
        elif payload.status != "published":
            document.published_by = None
            document.published_at = None
            document.vector_index_status = "disabled"
            document.vector_index_error = None
    append_audit_log(db, actor, "knowledge_document.updated", "knowledge_document", str(document.id), {"status": document.status, "version": document.version})
    db.commit()
    db.refresh(document)
    refreshed = document_dao.get_by_id(db, document.id) or document
    if refreshed.status == "published" and payload.status == "published" and (not was_published or content_changed):
        # 发布事务成功后再投递，索引失败只影响向量检索，不回滚文档发布。
        from app.services.knowledge_index_service import enqueue_knowledge_index

        enqueue_knowledge_index(refreshed.id)
    return refreshed


def search_published_documents(db: Session) -> list[tuple[KnowledgeChunk, KnowledgeDocument]]:
    return chunk_dao.list_published(db)
