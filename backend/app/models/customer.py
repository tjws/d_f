from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Customer(Base):
    """客户数据库模型，对应 customers 表。"""

    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    # 当前负责这条客户线索的销售用户。
    # 暂时允许为空，因为数据库中已经存在旧客户数据。
    owner_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"),
        nullable=True,
        index=True,
    )    

    name: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    phone: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    student_name: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    grade: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )

    interested_subject: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    stage: Mapped[str] = mapped_column(
        String(30),
        default="new",
        nullable=False,
    )

    source: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    remark: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    next_follow_up_at: Mapped[datetime | None] = mapped_column(
    DateTime(timezone=True),
    nullable=True,
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