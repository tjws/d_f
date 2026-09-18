from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.chat_message import ChatMessage


class ChatMessageDAO:
    def get_by_wecom_message_id(self, db: Session, message_id: str) -> ChatMessage | None:
        return db.scalar(select(ChatMessage).where(ChatMessage.wecom_message_id == message_id))

    def add(self, db: Session, message: ChatMessage) -> None:
        db.add(message)

    def list_by_customer(self, db: Session, customer_id: int) -> list[ChatMessage]:
        return list(db.scalars(select(ChatMessage).where(ChatMessage.customer_id == customer_id).order_by(ChatMessage.sent_at.desc(), ChatMessage.id.desc())).all())

    def list_after_id(self, db: Session, customer_id: int, after_id: int = 0) -> list[ChatMessage]:
        """按自增 ID 获取增量消息，避免侧边栏每次重载全部历史。"""
        return list(
            db.scalars(
                select(ChatMessage)
                .where(ChatMessage.customer_id == customer_id, ChatMessage.id > after_id)
                .order_by(ChatMessage.id.asc())
            ).all()
        )
