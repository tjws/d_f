from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.rag_evaluation_case import RAGEvaluationCase


class RAGEvaluationCaseDAO:
    """评测用例的数据访问；事务提交统一由 Service/API 控制。"""

    def get_by_id(self, db: Session, case_id: int) -> RAGEvaluationCase | None:
        return db.get(RAGEvaluationCase, case_id)

    def get_by_source(self, db: Session, source_type: str, source_id: str) -> RAGEvaluationCase | None:
        return db.scalar(
            select(RAGEvaluationCase).where(
                RAGEvaluationCase.source_type == source_type,
                RAGEvaluationCase.source_id == source_id,
            )
        )

    def list(self, db: Session, status: str | None = None, limit: int = 100) -> list[RAGEvaluationCase]:
        statement = select(RAGEvaluationCase).order_by(RAGEvaluationCase.created_at.desc()).limit(limit)
        if status:
            statement = statement.where(RAGEvaluationCase.status == status)
        return list(db.scalars(statement).all())

    def add(self, db: Session, case: RAGEvaluationCase) -> None:
        db.add(case)

