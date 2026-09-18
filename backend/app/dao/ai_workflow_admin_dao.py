from datetime import datetime

from sqlalchemy import and_, desc, or_, select
from sqlalchemy.orm import Session

from app.models.ai_workflow_run import AIWorkflowRun


class AIWorkflowAdminDAO:
    """管理后台运行历史的数据访问层；不读取 result_json 中的完整敏感内容。"""

    def list_recent(
        self,
        db: Session,
        start: datetime,
        end: datetime,
        provider_name: str | None,
        limit: int,
    ) -> list[AIWorkflowRun]:
        statement = (
            select(AIWorkflowRun)
            .where(AIWorkflowRun.created_at >= start, AIWorkflowRun.created_at < end)
            .order_by(desc(AIWorkflowRun.created_at))
        )
        if provider_name:
            statement = statement.where(AIWorkflowRun.provider_name == provider_name)
        statement = statement.limit(limit)
        return list(db.scalars(statement).all())

    def list_stale_running(
        self, db: Session, cutoff: datetime, limit: int
    ) -> list[AIWorkflowRun]:
        """只返回心跳超时的 running 任务，供人工确认后的恢复操作使用。"""

        statement = (
            select(AIWorkflowRun)
            .where(
                AIWorkflowRun.status == "running",
                or_(
                    AIWorkflowRun.heartbeat_at < cutoff,
                    and_(
                        AIWorkflowRun.heartbeat_at.is_(None),
                        AIWorkflowRun.started_at < cutoff,
                    ),
                ),
            )
            .order_by(AIWorkflowRun.started_at.asc())
            .limit(limit)
        )
        return list(db.scalars(statement).all())
