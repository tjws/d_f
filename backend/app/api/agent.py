from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.agent import AgentControlRequest, AgentRetryRequest, SalesAgentRead, SalesAgentRequest
from app.schemas.ai_suggestion_feedback import AgentFeedbackCreate, AgentFeedbackRead
from app.services.ai_suggestion_feedback_service import feedback_dao, record_agent_feedback
from app.services.customer_service import get_customer_or_404
from app.services.agent_service import run_sales_agent
from app.services.comprehensive_agent_service import (
    control_comprehensive_agent,
    get_comprehensive_agent_run,
    retry_comprehensive_agent_run,
)


router = APIRouter(prefix="/customers/{customer_id}/agent", tags=["agent"])


@router.post("/run", response_model=SalesAgentRead)
def run_customer_sales_agent(
    customer_id: int,
    payload: SalesAgentRequest | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """运行受控销售 Agent；输出仍然是待人工确认的建议或画像草稿。"""

    return run_sales_agent(db, customer_id, current_user, payload or SalesAgentRequest())


@router.post("/runs/{run_id}/control", response_model=SalesAgentRead)
def control_customer_sales_agent(
    customer_id: int,
    run_id: int,
    payload: AgentControlRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """在综合 Agent 检查点暂停、修正或继续；不会发送消息。"""

    return control_comprehensive_agent(db, customer_id, run_id, current_user, payload)


@router.get("/runs/{run_id}", response_model=SalesAgentRead)
def get_customer_sales_agent_run(
    customer_id: int,
    run_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """轮询综合 Agent 的步骤和状态，不会重新执行工具。"""

    return get_comprehensive_agent_run(db, customer_id, run_id, current_user)


@router.post("/runs/{run_id}/retry", response_model=SalesAgentRead)
def retry_customer_sales_agent(
    customer_id: int,
    run_id: int,
    payload: AgentRetryRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """失败后由人工明确确认再重试综合 Agent，不会自动发送或修改业务数据。"""

    return retry_comprehensive_agent_run(db, customer_id, run_id, current_user, payload.confirm)


@router.post("/runs/{run_id}/feedback", response_model=AgentFeedbackRead)
def submit_customer_sales_agent_feedback(
    customer_id: int,
    run_id: int,
    payload: AgentFeedbackCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """记录人工对综合 Agent 推理的纠错，不会触发发送或修改客户业务数据。"""

    feedback = record_agent_feedback(db, customer_id, run_id, current_user, payload.action, payload.note)
    db.commit()
    db.refresh(feedback)
    return feedback


@router.get("/runs/{run_id}/feedback", response_model=AgentFeedbackRead)
def get_customer_sales_agent_feedback(
    customer_id: int,
    run_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    get_customer_or_404(db, customer_id, current_user, "read")
    feedback = feedback_dao.get_by_target(db, "agent_run", str(run_id))
    if feedback is None or feedback.customer_id != customer_id:
        from fastapi import HTTPException, status

        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="该 Agent 运行尚无反馈")
    return feedback
