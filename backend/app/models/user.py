from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class User(Base):
    """系统用户模型，对应 users 表。"""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    username: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
        nullable=False,
    )

    full_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    # 这里只保存密码哈希，绝不能保存明文密码。
    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    # 先使用简单角色，后面扩展为完整 RBAC。
    role: Mapped[str] = mapped_column(
        String(30),
        default="sales",
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )