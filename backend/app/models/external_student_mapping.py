"""外部学生编号与系统学生的映射。"""

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ExternalStudentMapping(Base):
    """用来源命名空间隔离不同外部系统的学生编号。"""

    __tablename__ = "external_student_mappings"
    __table_args__ = (
        UniqueConstraint(
            "source_system",
            "external_student_id",
            name="uq_external_student_mappings_source_student",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    source_system: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    external_student_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
