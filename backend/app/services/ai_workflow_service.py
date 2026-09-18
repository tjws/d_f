import os
import logging
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.graph import customer_ai_graph
from app.ai.providers.factory import get_workflow_provider_name
from app.dao.ai_workflow_run_dao import AIWorkflowRunDAO
from app.dao.system_setting_dao import SystemSettingDAO
from app.db.session import SessionLocal
from app.models.ai_workflow_run import AIWorkflowRun
from app.models.customer_profile import CustomerProfile
from app.models.user import User
from app.services.customer_service import get_customer_or_404
from app.services.ai_rag_telemetry_service import record_rag_interaction


workflow_run_dao = AIWorkflowRunDAO()
system_setting_dao = SystemSettingDAO()
_VALID_GOALS = {"profile", "reply", "tag", "schedule"}
logger = logging.getLogger("k12.ai")


def max_workflow_attempts() -> int:
    """返回单次工作流允许的最大执行次数，默认 3 次并限制配置范围。"""

    try:
        configured = int(os.getenv("AI_WORKFLOW_MAX_ATTEMPTS", "3"))
    except ValueError:
        configured = 3
    return max(1, min(configured, 5))


def _utc_day_start() -> datetime:
    now = datetime.now(timezone.utc)
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def _daily_bailian_limit(db: Session) -> int:
    # 管理后台可调整全局上限；环境变量仍作为未迁移/未配置时的安全回退。
    env_default = max(0, int(os.getenv("AI_DAILY_BAILIAN_REQUEST_LIMIT", "20")))
    return system_setting_dao.get_global_int(db, "ai_daily_bailian_request_limit", env_default)


def ensure_bailian_capacity(db: Session, current_user: User, required_calls: int = 1) -> None:
    """在调用前预留当日额度，避免自动规划已计费却无额度生成草稿。"""

    limit = _daily_bailian_limit(db)
    used = workflow_run_dao.count_billable_since(db, current_user.id, _utc_day_start())
    if required_calls < 1 or limit == 0 or used + required_calls > limit:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="今日百炼调用额度不足")


def _result_payload(result: dict[str, object]) -> dict[str, object]:
    """只保留前端需要的结果索引，避免任务表复制任何敏感上下文。"""

    return {
        "customer_id": result.get("customer_id"),
        "status": result.get("status", "waiting_human"),
        "suggestion_ids": result.get("suggestion_ids", []),
        "customer_tag_ids": result.get("customer_tag_ids", []),
        "profile_id": result.get("profile_id"),
        "next_action": result.get("next_action"),
        "error": result.get("error"),
    }


def _read_run(run: AIWorkflowRun) -> dict[str, object]:
    result = run.result_json or {}
    return {
        "run_id": run.id,
        "customer_id": run.customer_id,
        "status": result.get("status", run.status),
        "suggestion_ids": result.get("suggestion_ids", []),
        "customer_tag_ids": result.get("customer_tag_ids", []),
        "profile_id": result.get("profile_id"),
        "next_action": result.get("next_action"),
        "error": result.get("error"),
        "attempt_count": run.attempt_count,
        "max_attempts": max_workflow_attempts(),
        "retryable": run.status == "failed" and run.attempt_count < max_workflow_attempts(),
    }


def _execution_mode() -> str:
    # 本地原有 API 与测试继续同步执行；Compose 明确指定 queue，避免隐藏的 Redis 依赖。
    return os.getenv("AI_WORKFLOW_EXECUTION_MODE", "sync").strip().lower()


def run_customer_ai_workflow(
    db: Session,
    customer_id: int,
    current_user: User,
    workflow_goal: str = "reply",
    idempotency_key: str | None = None,
    force_sync: bool = False,
) -> dict[str, object]:
    """创建一次可审计的 AI 运行；兼容旧同步接口时可强制等待同一条工作流。"""

    # Graph 内部还会再次检查操作者，但 API 层先做数据范围校验，避免越权读取上下文。
    customer = get_customer_or_404(db, customer_id, current_user, "update")
    if workflow_goal not in _VALID_GOALS:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="不支持的 AI 工作流目标")

    if idempotency_key:
        existing = workflow_run_dao.get_by_idempotency_key(
            db, customer_id, current_user.id, idempotency_key
        )
        if existing is not None:
            if existing.goal != workflow_goal:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="幂等键已经用于其他 AI 工作流目标")
            # 重复的网络请求直接读取原记录，不重新排队或再次调用模型。
            return _read_run(existing)

    has_confirmed_profile = db.scalar(
        select(CustomerProfile.id)
        .where(
            CustomerProfile.customer_id == customer.id,
            CustomerProfile.status == "confirmed",
        )
        .limit(1)
    ) is not None
    provider_name = get_workflow_provider_name(workflow_goal, has_confirmed_profile)
    if provider_name == "bailian":
        ensure_bailian_capacity(db, current_user)

    run = AIWorkflowRun(
        customer_id=customer_id,
        actor_user_id=current_user.id,
        goal=workflow_goal,
        provider_name=provider_name,
        status="queued",
        idempotency_key=idempotency_key,
    )
    workflow_run_dao.add(db, run)
    db.commit()
    db.refresh(run)
    logger.info("ai_workflow_queued", extra={"event": "ai_workflow_queued", "run_id": run.id, "customer_id": customer_id, "provider_name": provider_name})

    if _execution_mode() == "queue" and not force_sync:
        try:
            from app.workers.ai_workflow_tasks import execute_ai_workflow_task

            execute_ai_workflow_task.send(run.id)
        except Exception as exc:
            run.status = "failed"
            run.error_code = "queue_unavailable"
            run.result_json = {"status": "failed", "error": "AI 任务队列暂不可用"}
            run.finished_at = datetime.now(timezone.utc)
            db.commit()
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="AI 任务队列暂不可用") from exc
        return _read_run(run)

    execute_ai_workflow_run(run.id)
    db.expire_all()
    refreshed = workflow_run_dao.get_by_id(db, customer_id, run.id)
    if refreshed is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="AI 任务记录不存在")
    return _read_run(refreshed)


def execute_ai_workflow_run(run_id: int) -> None:
    """Worker 和同步模式共用的执行函数，保证结果总能回写任务表。"""

    with SessionLocal() as db:
        run = workflow_run_dao.get_by_id_for_update(db, run_id)
        if run is None or run.status not in {"queued", "running"}:
            return
        if run.status == "running":
            return
        run.status = "running"
        run.attempt_count += 1
        run.started_at = datetime.now(timezone.utc)
        run.heartbeat_at = run.started_at
        customer_id = run.customer_id
        provider_name = run.provider_name
        actor_user_id = run.actor_user_id
        goal = run.goal
        db.commit()
        logger.info("ai_workflow_started", extra={"event": "ai_workflow_started", "run_id": run_id, "customer_id": customer_id, "provider_name": provider_name})

    if actor_user_id is None:
        result: dict[str, object] = {"status": "failed", "error": "执行用户不存在"}
    else:
        try:
            result = customer_ai_graph.invoke(
                {
                    "customer_id": customer_id,
                "actor_user_id": actor_user_id,
                "workflow_goal": goal,
                }
            )
        except Exception:
            result = {"status": "failed", "error": "AI 工作流执行失败"}

    with SessionLocal() as db:
        run = workflow_run_dao.get_by_id_for_update(db, run_id)
        # 管理端可能已将失联任务标记为失败；不能让迟到的 Worker 结果覆盖人工恢复决定。
        if run is None or run.status != "running":
            return
        # Graph 只返回脱敏的 knowledge_policy；遥测不保存完整聊天正文。
        context = result.get("context") if isinstance(result, dict) else None
        policy = context.get("knowledge_policy") if isinstance(context, dict) else None
        if isinstance(policy, dict):
            suggestion_ids = result.get("suggestion_ids", []) if isinstance(result, dict) else []
            suggestion_id = next((int(value) for value in suggestion_ids if isinstance(value, int)), None) if isinstance(suggestion_ids, list) else None
            query = policy.get("query")
            record_rag_interaction(
                db,
                customer_id=run.customer_id,
                actor_user_id=run.actor_user_id,
                run_id=run.id,
                suggestion_id=suggestion_id,
                entrypoint="reply_workflow",
                query=str(query) if query is not None else None,
                retrieval_mode=str(policy.get("retrieval_mode", "keyword")),
                matched=bool(policy.get("matched", False)),
                fallback=bool(query) and not bool(policy.get("matched", False)),
                metadata={
                    "document_ids": [
                        str(item.get("document_id"))
                        for item in (context.get("knowledge", []) if isinstance(context, dict) else [])
                        if isinstance(item, dict) and item.get("document_id")
                    ][:10]
                },
            )
        payload = _result_payload({"customer_id": run.customer_id, **result})
        run.result_json = payload
        run.status = "failed" if payload["status"] == "failed" else "succeeded"
        run.error_code = "workflow_failed" if run.status == "failed" else None
        run.finished_at = datetime.now(timezone.utc)
        run.heartbeat_at = None
        db.commit()
        logger.info("ai_workflow_failed" if run.status == "failed" else "ai_workflow_succeeded", extra={"event": "ai_workflow_failed" if run.status == "failed" else "ai_workflow_succeeded", "run_id": run_id, "customer_id": run.customer_id, "provider_name": run.provider_name})


def get_customer_ai_workflow_run(
    db: Session,
    customer_id: int,
    run_id: int,
    current_user: User,
) -> dict[str, object]:
    """轮询任务状态前再次校验客户数据范围，不能借任务 ID 越权读取。"""

    get_customer_or_404(db, customer_id, current_user, "read")
    run = workflow_run_dao.get_by_id(db, customer_id, run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AI 工作流任务不存在")
    return _read_run(run)


def retry_customer_ai_workflow(
    db: Session,
    customer_id: int,
    run_id: int,
    current_user: User,
    confirm: bool,
) -> dict[str, object]:
    """人工确认后重新排队失败工作流；Worker 本身不会自动无限重试。"""

    get_customer_or_404(db, customer_id, current_user, "update")
    run = workflow_run_dao.get_by_id_for_update(db, run_id)
    if run is None or run.customer_id != customer_id or run.goal not in _VALID_GOALS:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AI 工作流任务不存在")
    if not confirm:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请明确确认后再重试 AI 任务")
    if run.status != "failed":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="只有失败任务可以重试")
    if run.attempt_count >= max_workflow_attempts():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="该任务已达到最大重试次数")
    if run.provider_name == "bailian":
        ensure_bailian_capacity(db, current_user)

    run.status = "queued"
    run.error_code = None
    run.started_at = None
    run.heartbeat_at = None
    run.finished_at = None
    run.result_json = {
        "status": "queued",
        "retry_of_attempt": run.attempt_count,
        "next_action": None,
    }
    db.commit()
    db.refresh(run)

    if _execution_mode() == "queue":
        try:
            from app.workers.ai_workflow_tasks import execute_ai_workflow_task

            execute_ai_workflow_task.send(run.id)
        except Exception as exc:
            run.status = "failed"
            run.error_code = "queue_unavailable"
            run.result_json = {"status": "failed", "error": "AI 任务队列暂不可用"}
            run.finished_at = datetime.now(timezone.utc)
            db.commit()
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="AI 任务队列暂不可用") from exc
        logger.info(
            "ai_workflow_retry_queued",
            extra={"event": "ai_workflow_retry_queued", "run_id": run.id, "customer_id": customer_id, "provider_name": run.provider_name},
        )
        return _read_run(run)

    execute_ai_workflow_run(run.id)
    db.expire_all()
    refreshed = workflow_run_dao.get_by_id(db, customer_id, run.id)
    if refreshed is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="AI 任务记录不存在")
    return _read_run(refreshed)
