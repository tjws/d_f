from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.ai_suggestion import AISuggestion


class AISuggestionDAO:
    """AI 建议的查询和新增操作，不在 DAO 内提交事务。"""

    def get_by_id(self, db: Session, customer_id: int, suggestion_id: int) -> AISuggestion | None:
        return db.scalar(select(AISuggestion).where(AISuggestion.customer_id == customer_id, AISuggestion.id == suggestion_id))

    def list_by_customer(self, db: Session, customer_id: int) -> list[AISuggestion]:
        return list(db.scalars(select(AISuggestion).where(AISuggestion.customer_id == customer_id).order_by(AISuggestion.created_at.desc(), AISuggestion.id.desc())).all())

    def list_by_customer_and_type(self, db: Session, customer_id: int, suggestion_type: str) -> list[AISuggestion]:
        return list(db.scalars(select(AISuggestion).where(AISuggestion.customer_id == customer_id, AISuggestion.suggestion_type == suggestion_type).order_by(AISuggestion.created_at.desc(), AISuggestion.id.desc())).all())

    def add(self, db: Session, suggestion: AISuggestion) -> None:
        db.add(suggestion)
