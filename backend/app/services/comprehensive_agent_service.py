"""第二层多工具 Agent 的业务编排层。

这里把“规划 -> 逐步查询 -> 汇总草稿 -> 人工确认”固定成一个可追踪流程。
所有工具都是只读查询；发送消息、确认建议等操作仍由原有业务 Service 处理。
"""

from copy import deepcopy
from datetime import datetime, timezone
import logging
import os
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.agent.comprehensive_planner import (
    ALLOWED_AGENT_TOOLS,
    MAX_AGENT_STEPS,
    ComprehensivePlanningError,
    get_comprehensive_planner,
)
from app.agent.comprehensive_tools import execute_comprehensive_tool
from app.agent.synthesis import synthesize_comprehensive_suggestion
from app.agent.tools import read_customer_snapshot
from app.dao.ai_suggestion_dao import AISuggestionDAO
from app.dao.ai_workflow_run_dao import AIWorkflowRunDAO
from app.db.session import SessionLocal
from app.models.ai_suggestion import AISuggestion
from app.models.ai_workflow_run import AIWorkflowRun
from app.models.user import User
from app.schemas.agent import AgentControlRequest
from app.services.ai_workflow_service import ensure_bailian_capacity, max_workflow_attempts
from app.services.audit_log_service import append_audit_log
from app.services.customer_service import get_customer_or_404
from app.services.system_setting_service import is_comprehensive_agent_enabled
from app.services.ai_rollout_service import require_rollout_access


workflow_run_dao = AIWorkflowRunDAO()
suggestion_dao = AISuggestionDAO()
logger = logging.getLogger("k12.ai")


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _queue_enabled() -> bool:
    """Compose 将该开关设为 queue；本地默认 sync，避免隐藏 Redis 依赖。"""

    return os.getenv("AI_WORKFLOW_EXECUTION_MODE", "sync").strip().lower() == "queue"


def _flatten_missing(steps: list[dict[str, Any]]) -> list[str]:
    return list(
        dict.fromkeys(
            str(item)
            for step in steps
            for item in step.get("missing_inputs", [])
            if isinstance(step, dict)
        )
    )


def _trace(plan_rationale: str, steps: list[dict[str, Any]], *, failed: bool = False) -> list[dict[str, str]]:
    trace: list[dict[str, str]] = [
        {
            "name": "agent.plan.read_only_tools",
            "status": "error" if failed else "ok",
            "detail": plan_rationale,
        }
    ]
    trace.extend(
        {
            "name": str(step.get("tool_name", "unknown")),
            "status": str(step.get("status", "error")),
            "detail": str(step.get("summary", "无摘要")),
        }
        for step in steps
    )
    trace.append(
        {
            "name": "human_confirmation.require",
            "status": "ok",
            "detail": "综合结果仍是待人工编辑的草稿，不会自动发送或修改业务数据。",
        }
    )
    return trace


def _workflow_payload(
    run: AIWorkflowRun,
    *,
    suggestion_ids: list[int],
    profile_id: int | None,
    next_action: str | None,
    error: str | None = None,
) -> dict[str, Any]:
    return {
        "run_id": run.id,
        "customer_id": run.customer_id,
        # paused 是人工检查点；不能把它误报成失败，否则前端会丢失继续执行入口。
        "status": run.status,
        "suggestion_ids": suggestion_ids,
        "customer_tag_ids": [],
        "profile_id": profile_id,
        "next_action": next_action,
        "error": error,
    }


def _agent_response(
    run: AIWorkflowRun,
    *,
    planner_name: str,
    plan_rationale: str,
    steps: list[dict[str, Any]],
    suggestion_ids: list[int],
    profile_id: int | None,
    next_action: str | None,
    reasoning_status: str,
    plan_tools: list[str] | None = None,
    error: str | None = None,
) -> dict[str, Any]:
    return {
        "agent_name": "sales-copilot-v3",
        "intent": "comprehensive",
        "selected_tool": "multi_step_reasoning",
        "planned_by": planner_name,
        "planner_run_id": None,
        "human_confirmation_required": True,
        "tool_trace": _trace(plan_rationale, steps, failed=reasoning_status == "failed"),
        "steps": steps,
        "workflow": _workflow_payload(
            run,
            suggestion_ids=suggestion_ids,
            profile_id=profile_id,
            next_action=next_action,
            error=error,
        ),
        "metadata": {
            "provider_mode": "five_read_only_tools",
            "reasoning_status": reasoning_status,
            "step_limit": MAX_AGENT_STEPS,
            "plan_rationale": plan_rationale,
            "plan_tools": plan_tools or [],
            "execution_mode": (run.result_json or {}).get("execution_mode", "complete"),
            "missing_inputs": _flatten_missing(steps),
        },
    }


def _profile_id_from_steps(steps: list[dict[str, Any]]) -> int | None:
    profile_step = next(
        (step for step in steps if step.get("tool_name") == "customer_profile.read_confirmed"),
        None,
    )
    if isinstance(profile_step, dict) and isinstance(profile_step.get("data"), dict):
        value = profile_step["data"].get("profile_id")
        return int(value) if isinstance(value, int) else None
    return None


def _finalize_comprehensive_run(
    db: Session,
    run: AIWorkflowRun,
    customer: Any,
    current_user: User,
    plan: dict[str, Any],
    steps: list[dict[str, Any]],
) -> dict[str, Any]:
    """保存失败或草稿结果；暂停状态不会走到这里。"""

    profile_id = _profile_id_from_steps(steps)
    if any(step.get("status") == "error" for step in steps):
        run.status = "failed"
        run.error_code = "agent_tool_failed"
        run.result_json = {
            "status": "failed",
            "error": "综合 Agent 查询失败",
            "agent_steps": steps,
            "plan_tool_names": plan["tool_names"],
            "plan_rationale": plan["rationale"],
            "reasoning_status": "failed",
        }
        run.finished_at = _utc_now()
        run.heartbeat_at = None
        db.commit()
        return _agent_response(
            run,
            planner_name=str(plan.get("provider_name", run.provider_name)),
            plan_rationale=str(plan["rationale"]),
            plan_tools=list(plan["tool_names"]),
            steps=steps,
            suggestion_ids=[],
            profile_id=profile_id,
            next_action=None,
            reasoning_status="failed",
            error="综合 Agent 查询失败",
        )

    suggestion_payload = synthesize_comprehensive_suggestion(
        {
            "interested_subject": customer.interested_subject,
            "grade": customer.grade,
        },
        steps,
    )
    suggestion = AISuggestion(
        customer_id=customer.id,
        user_id=current_user.id,
        profile_id=profile_id,
        suggestion_type="reply",
        content_json=suggestion_payload["content"],
        evidence_json=suggestion_payload["evidence"],
        evidence_level=suggestion_payload["evidence_level"],
        status="draft",
        model_name=suggestion_payload["model_name"],
        model_version=suggestion_payload["model_version"],
        prompt_version="agent-comprehensive-v1",
    )
    suggestion_dao.add(db, suggestion)
    db.flush()
    reasoning_status = "incomplete" if _flatten_missing(steps) else "succeeded"
    next_action = "confirm_profile" if "confirmed_profile" in _flatten_missing(steps) else "review_reply"
    append_audit_log(
        db,
        current_user,
        "customer.agent_comprehensive_generated",
        "ai_suggestion",
        str(suggestion.id),
        {
            "customer_id": customer.id,
            "workflow_run_id": run.id,
            "step_count": len(steps),
            "reasoning_status": reasoning_status,
            "human_confirmation_required": True,
        },
    )
    run.status = "waiting_human"
    run.error_code = None
    run.result_json = {
        "status": "waiting_human",
        "suggestion_ids": [suggestion.id],
        "profile_id": profile_id,
        "next_action": next_action,
        "agent_steps": steps,
        "plan_tool_names": plan["tool_names"],
        "plan_rationale": plan["rationale"],
        "reasoning_status": reasoning_status,
        "missing_inputs": _flatten_missing(steps),
    }
    run.finished_at = _utc_now()
    run.heartbeat_at = None
    db.commit()
    db.refresh(run)
    return _agent_response(
        run,
        planner_name=str(plan.get("provider_name", run.provider_name)),
        plan_rationale=str(plan["rationale"]),
        plan_tools=list(plan["tool_names"]),
        steps=steps,
        suggestion_ids=[suggestion.id],
        profile_id=profile_id,
        next_action=next_action,
        reasoning_status=reasoning_status,
    )


def run_comprehensive_agent(
    db: Session,
    customer_id: int,
    current_user: User,
    instruction: str | None = None,
    execution_mode: str = "complete",
    idempotency_key: str | None = None,
) -> dict[str, Any]:
    """执行一次五工具分析；checkpointed 模式在首个工具前保存人工检查点。"""

    customer = get_customer_or_404(db, customer_id, current_user, "update")
    require_rollout_access(db, current_user, "综合 Agent")
    if execution_mode not in {"complete", "checkpointed"}:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="不支持的 Agent 执行模式")
    if idempotency_key:
        existing = workflow_run_dao.get_by_idempotency_key(
            db, customer_id, current_user.id, idempotency_key
        )
        if existing is not None:
            if existing.goal != "agent_comprehensive":
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="幂等键已经用于其他 AI 工作流目标")
            try:
                plan = _plan_from_run(existing)
            except HTTPException:
                result = existing.result_json or {}
                return _agent_response(
                    existing,
                    planner_name=existing.provider_name,
                    plan_rationale="原 Agent 计划不可用",
                    plan_tools=[],
                    steps=[],
                    suggestion_ids=[],
                    profile_id=None,
                    next_action=None,
                    reasoning_status="failed",
                    error=str(result.get("error", "Agent 运行失败")),
                )
            return _control_response(db, existing, plan)
    if not is_comprehensive_agent_enabled(db):
        # 管理员可在高风险或成本异常时关停综合 Agent，退回普通单模块回复建议。
        append_audit_log(
            db,
            current_user,
            "customer.agent_comprehensive_disabled",
            "customer",
            str(customer_id),
            {"fallback": "reply", "reason": "global_kill_switch"},
        )
        from app.services.ai_workflow_service import run_customer_ai_workflow

        workflow = run_customer_ai_workflow(
            db, customer_id, current_user, "reply", idempotency_key
        )
        return {
            "agent_name": "sales-copilot-v3",
            "intent": "reply",
            "selected_tool": "generate_reply_draft",
            "planned_by": "explicit_task",
            "planner_run_id": None,
            "human_confirmation_required": True,
            "tool_trace": [
                {
                    "name": "agent.kill_switch",
                    "status": "skipped",
                    "detail": "综合 Agent 已由管理员关闭，已退回普通回复建议。",
                },
                {
                    "name": "human_confirmation.require",
                    "status": "ok",
                    "detail": "回复建议仍需人工编辑、确认和发送。",
                },
            ],
            "steps": [],
            "workflow": workflow,
            "metadata": {
                "provider_mode": "comprehensive_disabled_fallback",
                "reason": "global_kill_switch",
                "fallback_mode": "single_reply",
            },
        }
    snapshot = read_customer_snapshot(db, customer_id)
    planner = get_comprehensive_planner()
    if planner.provider_name == "bailian":
        # 规划阶段只调用一次百炼；工具本身全部是本地只读查询。
        ensure_bailian_capacity(db, current_user, required_calls=1)

    run = AIWorkflowRun(
        customer_id=customer_id,
        actor_user_id=current_user.id,
        goal="agent_comprehensive",
        provider_name=planner.provider_name,
        idempotency_key=idempotency_key,
        status="running" if execution_mode == "complete" else "paused",
        attempt_count=1 if execution_mode == "complete" else 0,
        started_at=_utc_now() if execution_mode == "complete" else None,
        heartbeat_at=_utc_now() if execution_mode == "complete" else None,
    )
    workflow_run_dao.add(db, run)
    db.commit()
    db.refresh(run)

    try:
        plan = planner.plan(snapshot, instruction)
    except ComprehensivePlanningError as exc:
        run.status = "failed"
        run.error_code = "agent_planning_failed"
        run.result_json = {"status": "failed", "error": "综合 Agent 规划失败"}
        run.finished_at = _utc_now()
        run.heartbeat_at = None
        db.commit()
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="综合 Agent 规划暂不可用") from exc

    tool_names = plan.get("tool_names", [])
    if not tool_names or len(tool_names) > MAX_AGENT_STEPS or any(name not in ALLOWED_AGENT_TOOLS for name in tool_names):
        run.status = "failed"
        run.error_code = "agent_plan_invalid"
        run.result_json = {"status": "failed", "error": "综合 Agent 规划包含非法工具"}
        run.finished_at = _utc_now()
        run.heartbeat_at = None
        db.commit()
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="综合 Agent 规划包含非法工具")

    if execution_mode == "checkpointed":
        # 计划和检查点只保存白名单名称，不保存原始聊天正文或模型推理内容。
        run.result_json = {
            "status": "paused",
            "agent_steps": [],
            "plan_tool_names": list(tool_names),
            "plan_rationale": str(plan["rationale"]),
            "next_step_index": 0,
            "corrections": {"skip_tools": [], "note": None},
            "reasoning_status": "paused",
            "next_action": "resume_agent",
            "execution_mode": "checkpointed",
        }
        db.commit()
        db.refresh(run)
        return _agent_response(
            run,
            planner_name=planner.provider_name,
            plan_rationale=str(plan["rationale"]),
            plan_tools=list(tool_names),
            steps=[],
            suggestion_ids=[],
            profile_id=None,
            next_action="resume_agent",
            reasoning_status="paused",
        )

    if _queue_enabled():
        # 规划已完成，后续只读工具交给 Worker；API 立即返回，前端可轮询同一 run_id。
        run.started_at = None
        run.status = "queued"
        run.result_json = {
            "status": "queued",
            "agent_steps": [],
            "plan_tool_names": list(tool_names),
            "plan_rationale": str(plan["rationale"]),
            "next_step_index": 0,
            "corrections": {"skip_tools": [], "note": None},
            "reasoning_status": "queued",
            "execution_mode": "complete",
            "execution_request": {"step_limit": len(tool_names)},
        }
        run.heartbeat_at = None
        db.commit()
        db.refresh(run)
        try:
            from app.workers.ai_workflow_tasks import execute_comprehensive_agent_task

            execute_comprehensive_agent_task.send(run.id)
        except Exception as exc:
            run.status = "failed"
            run.error_code = "queue_unavailable"
            run.result_json = {
                "status": "failed",
                "error": "Agent 任务队列暂不可用",
                "plan_tool_names": list(tool_names),
                "plan_rationale": str(plan["rationale"]),
                "agent_steps": [],
                "reasoning_status": "failed",
            }
            run.finished_at = _utc_now()
            run.heartbeat_at = None
            db.commit()
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Agent 任务队列暂不可用") from exc
        return _agent_response(
            run,
            planner_name=planner.provider_name,
            plan_rationale=str(plan["rationale"]),
            plan_tools=list(tool_names),
            steps=[],
            suggestion_ids=[],
            profile_id=None,
            next_action=None,
            reasoning_status="queued",
        )

    consultant_name = current_user.full_name or current_user.username
    steps: list[dict[str, Any]] = []
    for step_number, tool_name in enumerate(tool_names, start=1):
        try:
            result = execute_comprehensive_tool(
                db, customer_id, tool_name, consultant_name,
                run_id=run.id, actor_user_id=current_user.id,
            )
            steps.append(result.as_step(step_number))
        except Exception:
            # 不把底层异常和查询参数返回给前端；失败步骤会让综合结果进入失败态。
            steps.append(
                {
                    "step": step_number,
                    "tool_name": tool_name,
                    "status": "error",
                    "summary": "该资料域查询失败，需要人工重新核对。",
                    "data": {},
                    "evidence": [],
                    "missing_inputs": [tool_name],
                }
            )

    return _finalize_comprehensive_run(db, run, customer, current_user, plan, steps)


def _plan_from_run(run: AIWorkflowRun) -> dict[str, Any]:
    # SQLAlchemy JSON 字段不是可变对象跟踪类型；先复制，确保步骤追加能被提交到数据库。
    result = deepcopy(run.result_json or {})
    tool_names = result.get("plan_tool_names", [])
    if not isinstance(tool_names, list) or any(str(name) not in ALLOWED_AGENT_TOOLS for name in tool_names):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Agent 运行计划不存在或已损坏")
    return {
        "tool_names": [str(name) for name in tool_names],
        "rationale": str(result.get("plan_rationale", "已保存的只读工具计划")),
        "provider_name": run.provider_name,
    }


def _control_response(db: Session, run: AIWorkflowRun, plan: dict[str, Any], error: str | None = None) -> dict[str, Any]:
    result = run.result_json or {}
    steps = result.get("agent_steps", [])
    if not isinstance(steps, list):
        steps = []
    return _agent_response(
        run,
        planner_name=run.provider_name,
        plan_rationale=str(plan["rationale"]),
        plan_tools=list(plan["tool_names"]),
        steps=steps,
        suggestion_ids=[int(value) for value in result.get("suggestion_ids", []) if isinstance(value, int)],
        profile_id=result.get("profile_id") if isinstance(result.get("profile_id"), int) else None,
        next_action=result.get("next_action"),
        reasoning_status=str(result.get("reasoning_status", "paused")),
        error=error or result.get("error"),
    )


def control_comprehensive_agent(
    db: Session,
    customer_id: int,
    run_id: int,
    current_user: User,
    payload: AgentControlRequest,
) -> dict[str, Any]:
    """执行暂停、修正或分批继续；人工修正只影响白名单工具计划。"""

    get_customer_or_404(db, customer_id, current_user, "update")
    run = workflow_run_dao.get_by_id(db, customer_id, run_id)
    if run is None or run.goal != "agent_comprehensive":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="综合 Agent 运行不存在")
    plan = _plan_from_run(run)
    # JSON 字段不自动追踪原地 list 修改，复制后再写回确保检查点可恢复。
    result = deepcopy(run.result_json or {})
    steps = result.get("agent_steps", [])
    if not isinstance(steps, list):
        steps = []

    if payload.action == "pause":
        if run.status in {"waiting_human", "failed"}:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="当前运行已经结束")
        result["status"] = "paused"
        result["next_action"] = "resume_agent"
        result["pause_requested"] = True
        run.status = "paused"
        run.finished_at = None
        run.result_json = result
        db.commit()
        db.refresh(run)
        return _control_response(db, run, plan)

    if payload.action == "correct":
        if run.status != "paused":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="只能在暂停检查点修正 Agent 计划")
        correction = payload.correction
        skip_tools = list(dict.fromkeys(correction.skip_tools if correction else []))
        invalid = [tool for tool in skip_tools if tool not in ALLOWED_AGENT_TOOLS]
        if invalid:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="修正中包含不允许的工具")
        result["corrections"] = {"skip_tools": skip_tools, "note": correction.note if correction else None}
        result["next_action"] = "resume_agent"
        result["status"] = "paused"
        run.result_json = result
        db.commit()
        db.refresh(run)
        return _control_response(db, run, plan)

    if run.status != "paused":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="只有暂停中的 Agent 才能继续")

    if _queue_enabled():
        # 继续动作只负责投递；Worker 会在每个工具边界检查 pause_requested。
        result["status"] = "queued"
        result["next_action"] = "resume_agent"
        result["pause_requested"] = False
        result["execution_mode"] = "checkpointed"
        result["execution_request"] = {"step_limit": payload.step_limit}
        run.status = "queued"
        run.result_json = result
        db.commit()
        db.refresh(run)
        try:
            from app.workers.ai_workflow_tasks import execute_comprehensive_agent_task

            execute_comprehensive_agent_task.send(run.id)
        except Exception as exc:
            result["status"] = "paused"
            result["next_action"] = "resume_agent"
            result["pause_requested"] = False
            run.status = "paused"
            run.result_json = result
            db.commit()
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Agent 任务队列暂不可用") from exc
        return _control_response(db, run, plan)

    skip_tools = set((result.get("corrections") or {}).get("skip_tools", []))
    completed_tools = {str(step.get("tool_name")) for step in steps if isinstance(step, dict)}
    # 先把人工跳过的资料域记录为 skipped，保证轨迹完整且不会误认为查询成功。
    next_step_number = len(steps) + 1
    for tool_name in plan["tool_names"]:
        if tool_name in skip_tools and tool_name not in completed_tools:
            steps.append(
                {
                    "step": next_step_number,
                    "tool_name": tool_name,
                    "status": "skipped",
                    "summary": "已按人工修正跳过该资料域。",
                    "data": {},
                    "evidence": [],
                    "missing_inputs": [f"skipped:{tool_name}"],
                }
            )
            completed_tools.add(tool_name)
            next_step_number += 1

    remaining = [tool for tool in plan["tool_names"] if tool not in completed_tools]
    customer = get_customer_or_404(db, customer_id, current_user, "update")
    consultant_name = current_user.full_name or current_user.username
    for tool_name in remaining[: payload.step_limit]:
        try:
            tool_result = execute_comprehensive_tool(
                db, customer_id, tool_name, consultant_name,
                run_id=run.id, actor_user_id=current_user.id,
            )
            steps.append(tool_result.as_step(next_step_number))
        except Exception:
            steps.append(
                {
                    "step": next_step_number,
                    "tool_name": tool_name,
                    "status": "error",
                    "summary": "该资料域查询失败，需要人工重新核对。",
                    "data": {},
                    "evidence": [],
                    "missing_inputs": [tool_name],
                }
            )
        next_step_number += 1

    if any(step.get("status") == "error" for step in steps):
        return _finalize_comprehensive_run(db, run, customer, current_user, plan, steps)

    result["agent_steps"] = steps
    remaining_after = [tool for tool in plan["tool_names"] if tool not in {str(step.get("tool_name")) for step in steps}]
    if remaining_after:
        result["status"] = "paused"
        result["next_step_index"] = len(steps)
        result["next_action"] = "resume_agent"
        result["reasoning_status"] = "paused"
        run.status = "paused"
        run.finished_at = None
        run.result_json = result
        db.commit()
        db.refresh(run)
        return _control_response(db, run, plan)

    return _finalize_comprehensive_run(db, run, customer, current_user, plan, steps)


def _mark_worker_failure(db: Session, run: AIWorkflowRun, error_code: str, message: str) -> None:
    result = deepcopy(run.result_json or {})
    result.update({"status": "failed", "error": message, "reasoning_status": "failed"})
    run.status = "failed"
    run.error_code = error_code
    run.result_json = result
    run.finished_at = _utc_now()
    run.heartbeat_at = None
    db.commit()


def _pause_worker(db: Session, run: AIWorkflowRun, result: dict[str, Any], steps: list[dict[str, Any]]) -> None:
    result = deepcopy(result)
    result.update(
        {
            "status": "paused",
            "agent_steps": steps,
            "next_step_index": len(steps),
            "next_action": "resume_agent",
            "reasoning_status": "paused",
            "pause_requested": False,
        }
    )
    run.status = "paused"
    run.finished_at = None
    run.heartbeat_at = None
    run.result_json = result
    db.commit()


def execute_comprehensive_agent_run(run_id: int) -> None:
    """Worker 执行入口；每个只读工具完成后提交检查点，允许安全暂停。"""

    with SessionLocal() as db:
        run = workflow_run_dao.get_by_id_for_update(db, run_id)
        if run is None or run.goal != "agent_comprehensive" or run.status not in {"queued", "running"}:
            return
        try:
            plan = _plan_from_run(run)
        except HTTPException:
            _mark_worker_failure(db, run, "agent_plan_invalid", "Agent 运行计划不存在或已损坏")
            return

        actor = db.get(User, run.actor_user_id) if run.actor_user_id is not None else None
        if actor is None or not actor.is_active:
            _mark_worker_failure(db, run, "agent_actor_unavailable", "Agent 执行用户或客户不存在")
            return
        try:
            # 入队和真正执行之间客户归属可能变化，因此 Worker 再做一次数据权限校验。
            customer = get_customer_or_404(db, run.customer_id, actor, "update")
        except HTTPException:
            _mark_worker_failure(db, run, "agent_customer_unavailable", "Agent 执行用户或客户不存在")
            return

        result = deepcopy(run.result_json or {})
        execution_mode = str(result.get("execution_mode", "complete"))
        if execution_mode not in {"complete", "checkpointed"}:
            _mark_worker_failure(db, run, "agent_execution_mode_invalid", "Agent 执行模式无效")
            return
        request = result.get("execution_request") or {}
        raw_limit = request.get("step_limit", len(plan["tool_names"])) if isinstance(request, dict) else len(plan["tool_names"])
        step_limit = max(1, min(MAX_AGENT_STEPS, int(raw_limit)))
        run.status = "running"
        run.attempt_count += 1
        run.started_at = run.started_at or _utc_now()
        run.heartbeat_at = _utc_now()
        run.finished_at = None
        result["status"] = "running"
        result["pause_requested"] = bool(result.get("pause_requested", False))
        run.result_json = result
        db.commit()
        logger.info(
            "agent_comprehensive_started",
            extra={"event": "agent_comprehensive_started", "run_id": run.id, "customer_id": run.customer_id, "provider_name": run.provider_name},
        )

        steps = result.get("agent_steps", [])
        steps = deepcopy(steps) if isinstance(steps, list) else []
        processed = 0
        consultant_name = actor.full_name or actor.username

        while True:
            db.expire(run)
            db.refresh(run)
            # 管理端恢复失联任务后，迟到的 Worker 必须停止，避免覆盖 worker_lost 状态。
            if run.status != "running":
                return
            latest = deepcopy(run.result_json or {})
            if latest.get("pause_requested"):
                _pause_worker(db, run, latest, steps)
                logger.info(
                    "agent_comprehensive_paused",
                    extra={"event": "agent_comprehensive_paused", "run_id": run.id, "customer_id": run.customer_id, "provider_name": run.provider_name},
                )
                return

            stored_steps = latest.get("agent_steps", steps)
            steps = deepcopy(stored_steps) if isinstance(stored_steps, list) else steps
            skip_tools = set((latest.get("corrections") or {}).get("skip_tools", []))
            completed_tools = {str(step.get("tool_name")) for step in steps if isinstance(step, dict)}
            # 跳过也要落入轨迹，避免人工修正后看不出计划发生了什么。
            for tool_name in plan["tool_names"]:
                if tool_name in skip_tools and tool_name not in completed_tools:
                    steps.append(
                        {
                            "step": len(steps) + 1,
                            "tool_name": tool_name,
                            "status": "skipped",
                            "summary": "已按人工修正跳过该资料域。",
                            "data": {},
                            "evidence": [],
                            "missing_inputs": [f"skipped:{tool_name}"],
                        }
                    )
                    completed_tools.add(tool_name)

            remaining = [tool for tool in plan["tool_names"] if tool not in completed_tools]
            if not remaining or (execution_mode == "checkpointed" and processed >= step_limit):
                latest["agent_steps"] = steps
                run.result_json = latest
                db.commit()
                if remaining:
                    _pause_worker(db, run, latest, steps)
                    return
                _finalize_comprehensive_run(db, run, customer, actor, plan, steps)
                logger.info(
                    "agent_comprehensive_succeeded",
                    extra={"event": "agent_comprehensive_succeeded", "run_id": run.id, "customer_id": run.customer_id, "provider_name": run.provider_name},
                )
                return

            tool_name = remaining[0]
            # 每个只读工具调用前刷新租约，避免长时间任务被误判为失联。
            run.heartbeat_at = _utc_now()
            db.commit()
            try:
                tool_result = execute_comprehensive_tool(
                    db, customer.id, tool_name, consultant_name,
                    run_id=run.id, actor_user_id=actor.id,
                )
                steps.append(tool_result.as_step(len(steps) + 1))
            except Exception:
                steps.append(
                    {
                        "step": len(steps) + 1,
                        "tool_name": tool_name,
                        "status": "error",
                        "summary": "该资料域查询失败，需要人工重新核对。",
                        "data": {},
                        "evidence": [],
                        "missing_inputs": [tool_name],
                    }
                )
            processed += 1
            latest["agent_steps"] = steps
            latest["next_step_index"] = len(steps)
            latest["status"] = "running"
            run.result_json = latest
            run.heartbeat_at = _utc_now()
            db.commit()
            if steps[-1].get("status") == "error":
                _finalize_comprehensive_run(db, run, customer, actor, plan, steps)
                return


def get_comprehensive_agent_run(
    db: Session,
    customer_id: int,
    run_id: int,
    current_user: User,
) -> dict[str, Any]:
    """返回综合 Agent 的完整步骤轨迹，供前端轮询队列状态。"""

    get_customer_or_404(db, customer_id, current_user, "read")
    run = workflow_run_dao.get_by_id(db, customer_id, run_id)
    if run is None or run.goal != "agent_comprehensive":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="综合 Agent 运行不存在")
    return _control_response(db, run, _plan_from_run(run))


def retry_comprehensive_agent_run(
    db: Session,
    customer_id: int,
    run_id: int,
    current_user: User,
    confirm: bool,
) -> dict[str, Any]:
    """人工确认后重试综合 Agent；保留已成功的只读步骤，只重跑失败步骤。"""

    get_customer_or_404(db, customer_id, current_user, "update")
    run = workflow_run_dao.get_by_id_for_update(db, run_id)
    if run is None or run.customer_id != customer_id or run.goal != "agent_comprehensive":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="综合 Agent 任务不存在")
    if not confirm:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请明确确认后再重试 Agent 任务")
    if run.status != "failed":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="只有失败任务可以重试")
    if run.attempt_count >= max_workflow_attempts():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="该任务已达到最大重试次数")

    try:
        plan = _plan_from_run(run)
    except HTTPException as exc:
        # 规划阶段失败时没有可恢复的工具清单，需重新发起一次新的 Agent 请求。
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="规划阶段失败的 Agent 不能原地重试") from exc
    result = deepcopy(run.result_json or {})
    steps = result.get("agent_steps", [])
    if isinstance(steps, list):
        # 失败步骤没有可信结果，移除后 Worker 会按原计划重新执行；成功步骤保持不变。
        result["agent_steps"] = [step for step in steps if isinstance(step, dict) and step.get("status") != "error"]
    else:
        result["agent_steps"] = []
    result.update(
        {
            "status": "queued",
            "reasoning_status": "queued",
            "error": None,
            "next_action": None,
            "pause_requested": False,
            "execution_request": {"step_limit": len(plan["tool_names"])},
        }
    )
    run.status = "queued"
    run.error_code = None
    run.started_at = None
    run.heartbeat_at = None
    run.finished_at = None
    run.result_json = result
    db.commit()
    db.refresh(run)

    if _queue_enabled():
        try:
            from app.workers.ai_workflow_tasks import execute_comprehensive_agent_task

            execute_comprehensive_agent_task.send(run.id)
        except Exception as exc:
            _mark_worker_failure(db, run, "queue_unavailable", "Agent 任务队列暂不可用")
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Agent 任务队列暂不可用") from exc
        logger.info(
            "agent_comprehensive_retry_queued",
            extra={"event": "agent_comprehensive_retry_queued", "run_id": run.id, "customer_id": customer_id, "provider_name": run.provider_name},
        )
        return _control_response(db, run, plan)

    execute_comprehensive_agent_run(run.id)
    db.expire_all()
    refreshed = workflow_run_dao.get_by_id(db, customer_id, run.id)
    if refreshed is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Agent 任务记录不存在")
    return _control_response(db, refreshed, _plan_from_run(refreshed))


__all__ = [
    "run_comprehensive_agent",
    "control_comprehensive_agent",
    "execute_comprehensive_agent_run",
    "get_comprehensive_agent_run",
    "retry_comprehensive_agent_run",
]
