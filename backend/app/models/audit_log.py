"""审计日志 ORM 模型。"""

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AuditLog(Base):
    """记录管理行为的不可变业务证据，对应 audit_logs 表。"""

    __tablename__ = "audit_logs"

    __table_args__ = (
        Index(
            "ix_audit_logs_target_type_target_id",
            "target_type",
            "target_id",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    # 用户被删除时保留审计记录，并将关联用户 ID 置空。
    actor_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # 保存操作发生时的身份快照，避免用户信息变化后无法追溯。
    actor_username_snapshot: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    actor_role_snapshot: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )

    # 区分接口、维护脚本和系统任务产生的操作。
    actor_source: Mapped[str] = mapped_column(
        String(30),
        default="api",
        nullable=False,
    )

    # 使用稳定的动作编码，例如 user.role_changed。
    action: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    # 目标可能来自不同表，因此使用类型加标识的组合。
    target_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    target_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    # 只保存必要差异，不保存密码、令牌或敏感明文。
    detail_json: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
    )

    result: Mapped[str] = mapped_column(
        String(20),
        default="success",
        nullable=False,
    )

    ip_address: Mapped[str | None] = mapped_column(
        String(45),
        nullable=True,
    )

    request_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )