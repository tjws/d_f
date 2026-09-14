from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
# 加载组织模型，使 users 的字符串外键注册到同一份 metadata。
from app.models.organization import Organization  # noqa: F401


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

    # 暂时允许为空，便于兼容已经存在的用户。
    organization_id: Mapped[int | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # 企业微信内部成员的唯一标识；本地账号可以暂时为空。
    wecom_userid: Mapped[str | None] = mapped_column(
        String(100),
        unique=True,
        index=True,
        nullable=True,
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
