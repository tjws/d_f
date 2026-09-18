from datetime import datetime

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models.ai_suggestion_feedback import AISuggestionFeedback
from app.models.chat_message import ChatMessage


class AdminRetentionDAO:
    """只处理可受控清理的数据集；审计日志和客户数据不开放删除。"""

    _models = {
        "chat_messages": ChatMessage,
        "ai_feedback": AISuggestionFeedback,
    }

    def preview(self, db: Session, dataset: str, before: datetime) -> tuple[int, datetime | None, datetime | None]:
        model = self._models[dataset]
        base = select(func.count(model.id), func.min(model.created_at), func.max(model.created_at)).where(model.created_at < before)
        count, oldest, newest = db.execute(base).one()
        return int(count or 0), oldest, newest

    def delete_before(self, db: Session, dataset: str, before: datetime) -> int:
        model = self._models[dataset]
        result = db.execute(delete(model).where(model.created_at < before))
        return int(result.rowcount or 0)
