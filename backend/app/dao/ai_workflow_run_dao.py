from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.ai_workflow_run import AIWorkflowRun


class AIWorkflowRunDAO:
    """AI 运行记录的数据访问层；事务仍由 Service 统一决定。"""

    def add(self, db: Session, run: AIWorkflowRun) -> None:
        db.add(run)

    def get_by_id(self, db: Session, customer_id: int, run_id: int) -> AIWorkflowRun | None:
        return db.scalar(
            select(AIWorkflowRun).where(
                AIWorkflowRun.customer_id == customer_id,
                AIWorkflowRun.id == run_id,
            )
        )

    def get_by_id_for_update(self, db: Session, run_id: int) -> AIWorkflowRun | None:
        return db.scalar(select(AIWorkflowRun).where(AIWorkflowRun.id == run_id).with_for_update())

    def get_by_idempotency_key(
        self,
        db: Session,
        customer_id: int,
        actor_user_id: int,
        idempotency_key: str,
    ) -> AIWorkflowRun | None:
        """查找同一次用户请求，重复提交时直接返回原运行记录。"""

        return db.scalar(
            select(AIWorkflowRun).where(
                AIWorkflowRun.customer_id == customer_id,
                AIWorkflowRun.actor_user_id == actor_user_id,
                AIWorkflowRun.idempotency_key == idempotency_key,
            )
        )

    def count_billable_since(self, db: Session, actor_user_id: int, since: datetime) -> int:
        """统计已入队的百炼请求，失败调用也计入，避免靠失败循环绕开限额。"""

        return int(
            db.scalar(
                select(func.count(AIWorkflowRun.id)).where(
                    AIWorkflowRun.actor_user_id == actor_user_id,
                    AIWorkflowRun.provider_name == "bailian",
                    AIWorkflowRun.created_at >= since,
                )
            )
            or 0
        )
