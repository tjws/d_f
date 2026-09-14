from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ChatMessage(Base):
    """客户聊天消息索引及其加密内容。"""

    __tablename__ = "chat_messages"
    __table_args__ = (
        UniqueConstraint(
            "wecom_message_id",
            name="uq_chat_messages_wecom_message_id",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    # 外部消息必须绑定一个本地客户，客户删除时一并删除消息。
    customer_id: Mapped[int] = mapped_column(
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # 关联处理或发送消息的内部用户；用户删除后保留消息记录。
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # 企业微信消息编号用于幂等，避免回调重试产生重复消息。
    wecom_message_id: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    direction: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
    )

    message_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        index=True,
    )

    # 原文只以 AES-GCM 密文保存；非文本消息可以没有内容正文。
    content_encrypted: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # 脱敏内容供列表和后续 AI 流程使用，不替代原文加密存储。
    content_masked: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    media_object_key: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
