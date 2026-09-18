"""异步 AI 工作流的运行记录。

这张表记录一次“用户点击生成”到“生成草稿结束”的过程。它不是建议本身，
也不会保存或触发任何自动发送行为。
"""

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AIWorkflowRun(Base):
    """AI 工作流的可观察任务状态，PostgreSQL 是任务结果的事实来源。"""

    __tablename__ = "ai_workflow_runs"
    __table_args__ = (
        Index("ix_ai_workflow_runs_actor_created", "actor_user_id", "created_at"),
        Index("ix_ai_workflow_runs_customer_status", "customer_id", "status"),
        # 同一操作者的同一个幂等键只能对应一条运行记录，避免重复点击产生重复 AI 任务。
        Index("uq_ai_workflow_runs_actor_idempotency", "actor_user_id", "idempotency_key", unique=True),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    customer_id: Mapped[int] = mapped_column(
        ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    actor_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    goal: Mapped[str] = mapped_column(String(20), nullable=False)
    provider_name: Mapped[str] = mapped_column(String(30), nullable=False, default="mock")
    idempotency_key: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="queued", index=True)
    attempt_count: Mapped[int] = mapped_column(nullable=False, default=0)

    # 只保存结果索引和可展示状态，不写入原始敏感上下文或 API 密钥。
    result_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Worker 执行期间定期刷新；管理端据此识别异常退出后遗留的 running 任务。
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
