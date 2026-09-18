from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.ai_suggestion_feedback import AISuggestionFeedback


class AISuggestionFeedbackDAO:
    """反馈读写，不在 DAO 内提交事务。"""

    def get_by_suggestion(self, db: Session, suggestion_id: int) -> AISuggestionFeedback | None:
        return db.scalar(select(AISuggestionFeedback).where(AISuggestionFeedback.suggestion_id == suggestion_id))

    def get_by_target(self, db: Session, target_type: str, target_id: str) -> AISuggestionFeedback | None:
        return db.scalar(select(AISuggestionFeedback).where(AISuggestionFeedback.target_type == target_type, AISuggestionFeedback.target_id == target_id))

    def add(self, db: Session, feedback: AISuggestionFeedback) -> None:
        db.add(feedback)
