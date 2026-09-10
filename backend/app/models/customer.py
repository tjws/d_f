from datetime import datetime, timezone

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Customer(Base):
    """客户数据库模型，对应 customers 表。"""

    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
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