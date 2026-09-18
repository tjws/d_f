from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.knowledge_chunk import KnowledgeChunk
from app.models.knowledge_document import KnowledgeDocument


class KnowledgeChunkDAO:
    def list_published(self, db: Session) -> list[tuple[KnowledgeChunk, KnowledgeDocument]]:
        statement = (
            select(KnowledgeChunk, KnowledgeDocument)
            .join(KnowledgeDocument, KnowledgeDocument.id == KnowledgeChunk.document_id)
            .where(KnowledgeDocument.status == "published")
            .order_by(KnowledgeDocument.id, KnowledgeChunk.chunk_index)
        )
        return list(db.execute(statement).all())

