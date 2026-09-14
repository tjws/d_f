from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class TimelineEvent(Base):
    """客户时间线事件，统一记录人工、系统和企业微信相关摘要。"""

    __tablename__ = "timeline_events"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    # 事件属于哪个客户；删除客户时同步删除其时间线。
    customer_id: Mapped[int] = mapped_column(
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # 产生事件的内部用户；用户删除后保留事件但清空操作员。
    operator_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    # 例如 manual_follow_up、student_created、wecom_message。
    event_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    # 时间线可能包含敏感内容，只保存加密后的摘要。
    summary_encrypted: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    # 例如 manual、wecom、system、ai。
    source: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    # 可选地关联学生、聊天消息或订单。
    reference_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    reference_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )