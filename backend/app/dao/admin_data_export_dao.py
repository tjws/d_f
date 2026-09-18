from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.ai_suggestion_feedback import AISuggestionFeedback
from app.models.audit_log import AuditLog
from app.models.chat_message import ChatMessage
from app.models.customer import Customer
from app.models.user import User


class AdminDataExportDAO:
    """按时间范围读取可导出的数据，不在 DAO 中解密或提交事务。"""

    @staticmethod
    def _apply_range(statement, column, start: datetime | None, end: datetime | None):
        if start is not None:
            statement = statement.where(column >= start)
        if end is not None:
            statement = statement.where(column <= end)
        return statement

    def list_customers(self, db: Session, start: datetime | None, end: datetime | None, limit: int):
        statement = select(Customer, User).outerjoin(User, User.id == Customer.owner_id)
        statement = self._apply_range(statement, Customer.created_at, start, end)
        return list(db.execute(statement.order_by(Customer.created_at.asc(), Customer.id.asc()).limit(limit)).all())

    def list_chat_messages(self, db: Session, start: datetime | None, end: datetime | None, limit: int):
        statement = select(ChatMessage, Customer, User).join(Customer, Customer.id == ChatMessage.customer_id).outerjoin(User, User.id == ChatMessage.user_id)
        statement = self._apply_range(statement, ChatMessage.created_at, start, end)
        return list(db.execute(statement.order_by(ChatMessage.created_at.asc(), ChatMessage.id.asc()).limit(limit)).all())

    def list_audit_logs(self, db: Session, start: datetime | None, end: datetime | None, limit: int):
        statement = self._apply_range(select(AuditLog), AuditLog.created_at, start, end)
        return list(db.scalars(statement.order_by(AuditLog.created_at.asc(), AuditLog.id.asc()).limit(limit)).all())

    def list_feedback(self, db: Session, start: datetime | None, end: datetime | None, limit: int):
        statement = self._apply_range(select(AISuggestionFeedback), AISuggestionFeedback.created_at, start, end)
        return list(db.scalars(statement.order_by(AISuggestionFeedback.created_at.asc(), AISuggestionFeedback.id.asc()).limit(limit)).all())
