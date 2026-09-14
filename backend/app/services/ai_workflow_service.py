from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.ai.graph import customer_ai_graph
from app.models.user import User
from app.services.customer_service import get_customer_or_404


def run_customer_ai_workflow(
    db: Session,
    customer_id: int,
    current_user: User,
) -> dict[str, object]:
    """校验客户权限后运行 Graph，并把结果交给人工确认流程。"""

    # Graph 内部还会再次检查操作者，但 API 层先做数据范围校验，避免越权读取上下文。
    get_customer_or_404(db, customer_id, current_user, "update")
    result = customer_ai_graph.invoke(
        {
            "customer_id": customer_id,
            "actor_user_id": current_user.id,
        }
    )

    if result.get("status") == "failed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=result.get("error", "AI workflow failed"),
        )

    return {
        "customer_id": customer_id,
        "status": result.get("status", "waiting_human"),
        "suggestion_ids": result.get("suggestion_ids", []),
        "error": result.get("error"),
    }
