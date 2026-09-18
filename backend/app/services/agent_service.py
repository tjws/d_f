from datetime import datetime, timezone
from typing import Any
import logging

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.agent.planner import AgentPlanningError, get_agent_planner
from app.agent.router import choose_goal
from app.agent.tools import allowed_tool_trace, read_customer_snapshot
from app.dao.ai_workflow_run_dao import AIWorkflowRunDAO
from app.models.ai_workflow_run import AIWorkflowRun
from app.models.user import User
from app.schemas.agent import SalesAgentRequest
from app.services.ai_workflow_service import (
    ensure_bailian_capacity,
    get_customer_ai_workflow_run,
    run_customer_ai_workflow,
)
from app.services.customer_service import get_customer_or_404
from app.services.comprehensive_agent_service import run_comprehensive_agent


logger = logging.getLogger("k12.ai")
workflow_run_dao = AIWorkflowRunDAO()


def _create_planning_run(db: Session, customer_id: int, actor_user_id: int, provider_name: str) -> AIWorkflowRun:
    """把一次外部规划调用落为最小可观察记录，不保存指令或模型推理。"""

    run = AIWorkflowRun(
        customer_id=customer_id,
        actor_user_id=actor_user_id,
        goal="agent_plan",
        provider_name=provider_name,
        status="running",
        attempt_count=1,
        started_at=datetime.now(timezone.utc),
    )
    workflow_run_dao.add(db, run)
    db.commit()
    db.refresh(run)
    return run


def _finish_planning_run(db: Session, run: AIWorkflowRun, *, selected_tool: str | None = None) -> None:
    run.finished_at = datetime.now(timezone.utc)
    if selected_tool is None:
        run.status = "failed"
        run.error_code = "agent_planning_failed"
        run.result_json = {"status": "failed", "error": "AI Agent 规划失败"}
    else:
        run.status = "succeeded"
        run.error_code = None
        run.result_json = {
            "status": "succeeded",
            "selected_tool": selected_tool,
            "human_confirmation_required": True,
        }
    db.commit()


def run_sales_agent(
    db: Session,
    customer_id: int,
    current_user: User,
    payload: SalesAgentRequest,
) -> dict[str, Any]:
    """执行受控 Agent：受限规划后，只交给既有 LangGraph 生成待确认草稿。"""

    # Agent 入口仍按客户更新权限校验，防止通过 Agent 间接越权读取或生成建议。
    get_customer_or_404(db, customer_id, current_user, "update")
    if payload.task == "comprehensive":
        return run_comprehensive_agent(
            db,
            customer_id,
            current_user,
            payload.instruction,
            payload.execution_mode,
            payload.idempotency_key,
        )
    if payload.idempotency_key:
        existing = workflow_run_dao.get_by_idempotency_key(
            db, customer_id, current_user.id, payload.idempotency_key
        )
        if existing is not None:
            if existing.goal not in {"reply", "tag", "schedule"}:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="幂等键已经用于其他 AI 工作流目标")
            stored_workflow = get_customer_ai_workflow_run(db, customer_id, existing.id, current_user)
            selected = {
                "reply": "generate_reply_draft",
                "tag": "generate_tag_suggestions",
                "schedule": "generate_schedule_suggestion",
            }[existing.goal]
            return {
                "agent_name": "sales-copilot-v2",
                "intent": existing.goal,
                "selected_tool": selected,
                "planned_by": "explicit_task",
                "planner_run_id": None,
                "human_confirmation_required": True,
                "tool_trace": [],
                "workflow": stored_workflow,
                "metadata": {"provider_mode": "controlled_tool_selection", "idempotent_replay": True},
            }
    snapshot = read_customer_snapshot(db, customer_id)
    planner_run_id: int | None = None
    if payload.task == "auto":
        planner = get_agent_planner()
        # 自动模式要预留“规划 + 生成草稿”两次百炼调用，避免只完成前半步。
        if planner.provider_name == "bailian":
            ensure_bailian_capacity(db, current_user, required_calls=2)
        planning_run = _create_planning_run(db, customer_id, current_user.id, planner.provider_name)
        planner_run_id = planning_run.id
        logger.info("agent_plan_started", extra={"event": "agent_plan_started", "run_id": planning_run.id, "customer_id": customer_id, "provider_name": planner.provider_name})
        try:
            plan = planner.plan(snapshot, payload.instruction)
        except AgentPlanningError as exc:
            _finish_planning_run(db, planning_run)
            logger.info("agent_plan_failed", extra={"event": "agent_plan_failed", "run_id": planning_run.id, "customer_id": customer_id, "provider_name": planner.provider_name})
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="AI Agent 规划暂不可用，请稍后重试") from exc
        _finish_planning_run(db, planning_run, selected_tool=plan["tool_name"])
        goal = plan["goal"]
        selected_tool = plan["tool_name"]
        planned_by = plan["provider_name"]
        logger.info("agent_plan_succeeded", extra={"event": "agent_plan_succeeded", "run_id": planning_run.id, "customer_id": customer_id, "provider_name": planner.provider_name})
    else:
        goal = choose_goal(payload.task, None)
        selected_tool = {
            "reply": "generate_reply_draft",
            "tag": "generate_tag_suggestions",
            "schedule": "generate_schedule_suggestion",
        }[goal]
        planned_by = "explicit_task"
    workflow = run_customer_ai_workflow(
        db,
        customer_id,
        current_user,
        goal,
        payload.idempotency_key,
    )
    # 只记录路由结果和运行编号，不把用户指令或聊天正文写入普通日志。
    logger.info(
        "sales_agent_routed",
        extra={
            "event": "sales_agent_routed",
            "run_id": workflow.get("run_id"),
            "customer_id": customer_id,
            "provider_name": "existing-workflow",
            "agent_name": "sales-copilot-v2",
            "intent": goal,
        },
    )
    return {
        "agent_name": "sales-copilot-v2",
        "intent": goal,
        "selected_tool": selected_tool,
        "planned_by": planned_by,
        "planner_run_id": planner_run_id,
        "human_confirmation_required": True,
        "tool_trace": allowed_tool_trace(snapshot, selected_tool),
        "workflow": workflow,
        "metadata": {
            "provider_mode": "controlled_tool_selection",
            "instruction_used_for_planning": bool(payload.instruction),
        },
    }
