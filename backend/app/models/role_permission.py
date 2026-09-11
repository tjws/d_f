from datetime import datetime, timezone

from sqlalchemy import DateTime, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class RolePermission(Base):
    """角色权限配置，对应 role_permissions 表。"""

    __tablename__ = "role_permissions"
    __table_args__ = (
        UniqueConstraint(
            "role",
            "module",
            "action",
            name="uq_role_permissions_role_module_action",
        ),
        Index("ix_role_permissions_role", "role"),
        Index("ix_role_permissions_module", "module"),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    # 第一版固定使用 admin、manager、sales 三种角色。
    role: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    module: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    action: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    # 数据范围先使用 own、team、organization、all 四种约定值。
    data_scope: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
