from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, Index, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SystemSetting(Base):
    """非敏感运行参数；密钥和 provider 凭据仍只允许来自环境变量。"""

    __tablename__ = "system_settings"
    __table_args__ = (
        UniqueConstraint("key", "scope_type", "scope_id", name="uq_system_settings_key_scope"),
        Index("ix_system_settings_key", "key"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(100), nullable=False)
    value_json: Mapped[Any] = mapped_column(JSON, nullable=False)
    scope_type: Mapped[str] = mapped_column(String(30), nullable=False, default="global")
    scope_id: Mapped[int | None] = mapped_column(nullable=True)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    updated_by: Mapped[int | None] = mapped_column(nullable=True, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
