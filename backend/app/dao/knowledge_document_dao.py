from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.knowledge_document import KnowledgeDocument


class KnowledgeDocumentDAO:
    def list_all(self, db: Session) -> list[KnowledgeDocument]:
        return list(db.scalars(select(KnowledgeDocument).options(selectinload(KnowledgeDocument.chunks)).order_by(KnowledgeDocument.updated_at.desc())).all())

    def get_by_id(self, db: Session, document_id: int) -> KnowledgeDocument | None:
        return db.scalar(select(KnowledgeDocument).options(selectinload(KnowledgeDocument.chunks)).where(KnowledgeDocument.id == document_id))

    def get_by_slug(self, db: Session, slug: str) -> KnowledgeDocument | None:
        return db.scalar(select(KnowledgeDocument).where(KnowledgeDocument.slug == slug))

    def add(self, db: Session, document: KnowledgeDocument) -> None:
        db.add(document)

