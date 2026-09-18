from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, ForeignKey, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Student(Base):
    """客户名下的学生资料，一个客户可以对应多个学生。"""

    __tablename__ = "students"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    # 禁止删除仍有关联学生的客户，避免误删业务资料。
    customer_id: Mapped[int] = mapped_column(
        ForeignKey("customers.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # 敏感姓名只保存加密结果，不保存明文。
    name_encrypted: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    gender: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    grade: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # 学校信息也按敏感信息处理。
    school_encrypted: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    birth_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    subjects_json: Mapped[dict | None] = mapped_column(
        JSON,
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

    # 软归档保留历史关系，同时让归档学生不再进入默认 AI 上下文。
    archived_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )
