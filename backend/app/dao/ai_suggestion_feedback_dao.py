from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.ai_suggestion_feedback import AISuggestionFeedback


class AISuggestionFeedbackDAO:
    """反馈读写，不在 DAO 内提交事务。"""

    def get_by_suggestion(self, db: Session, suggestion_id: int) -> AISuggestionFeedback | None:
        return db.scalar(select(AISuggestionFeedback).where(AISuggestionFeedback.suggestion_id == suggestion_id))

    def get_by_target(
        self,
        db: Session,
        customer_id: int,
        target_type: str,
        target_id: str,
    ) -> AISuggestionFeedback | None:
        """按客户范围读取反馈，避免历史编号复用造成跨客户冲突。"""

        return db.scalar(
            select(AISuggestionFeedback).where(
                AISuggestionFeedback.customer_id == customer_id,
                AISuggestionFeedback.target_type == target_type,
                AISuggestionFeedback.target_id == target_id,
            )
        )

    def add(self, db: Session, feedback: AISuggestionFeedback) -> None:
        db.add(feedback)
