from copy import deepcopy
from datetime import datetime, timedelta, timezone
import logging

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.dao.ai_workflow_admin_dao import AIWorkflowAdminDAO
from app.models.ai_workflow_run import AIWorkflowRun
from app.models.user import User
from app.services.ai_workflow_service import max_workflow_attempts


workflow_admin_dao = AIWorkflowAdminDAO()
logger = logging.getLogger("k12.ai")


def _effective_status(run: AIWorkflowRun) -> str:
    result_status = (run.result_json or {}).get("status")
    if result_status == "waiting_human":
        return "waiting_human"
    return run.status


def _to_read(run: AIWorkflowRun) -> dict[str, object]:
    result = run.result_json or {}
    suggestion_ids = result.get("suggestion_ids", [])
    return {
        "id": run.id,
        "customer_id": run.customer_id,
        "actor_user_id": run.actor_user_id,
        "goal": run.goal,
        "provider_name": run.provider_name,
        "status": _effective_status(run),
        "attempt_count": run.attempt_count,
        "error_code": run.error_code,
        "next_action": result.get("next_action"),
        "suggestion_count": len(suggestion_ids) if isinstance(suggestion_ids, list) else 0,
        "created_at": run.created_at,
        "started_at": run.started_at,
        "heartbeat_at": run.heartbeat_at,
        "finished_at": run.finished_at,
        "max_attempts": max_workflow_attempts(),
        "retryable": run.status == "failed" and run.attempt_count < max_workflow_attempts(),
    }


def list_workflow_runs(
    db: Session,
    start: datetime | None,
    end: datetime | None,
    provider_name: str | None,
    status_filter: str | None,
    limit: int,
) -> dict[str, object]:
    end_at = end or datetime.now(timezone.utc)
    start_at = start or (end_at - timedelta(days=7))
    if end_at <= start_at or (end_at - start_at).days > 31:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="时间范围必须在 0 到 31 天内",
        )
    normalized_provider = provider_name.strip().lower() if provider_name else None
    if normalized_provider and normalized_provider not in {"bailian", "mock"}:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="不支持的 Provider")
    allowed_statuses = {"queued", "running", "paused", "waiting_human", "succeeded", "failed"}
    if status_filter and status_filter not in allowed_statuses:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="不支持的运行状态")

    # 多取少量记录后再按 waiting_human 这种派生状态过滤，避免依赖特定数据库 JSON 查询语法。
    runs = workflow_admin_dao.list_recent(db, start_at, end_at, normalized_provider, 500)
    items = [_to_read(run) for run in runs]
    if status_filter:
        items = [item for item in items if item["status"] == status_filter]
    total = len(items)
    items = items[:limit]
    return {"items": items, "total": total}


def recover_stale_workflow_runs(
    db: Session,
    current_user: User,
    confirm: bool,
    stale_after_seconds: int,
    limit: int,
) -> dict[str, object]:
    """将确认过的失联 Worker 任务标为失败，不自动重新调用模型。"""

    if not confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请明确确认后再标记异常任务",
        )

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(seconds=stale_after_seconds)
    runs = workflow_admin_dao.list_stale_running(db, cutoff, limit)
    run_ids: list[int] = []
    for run in runs:
        result = deepcopy(run.result_json or {})
        result.update(
            {
                "status": "failed",
                "error": "Worker 心跳超时，任务需要人工重试",
                "recovery": "stale_worker",
                "stale_at": now.isoformat(),
            }
        )
        run.status = "failed"
        run.error_code = "worker_lost"
        run.result_json = result
        run.finished_at = now
        run.heartbeat_at = None
        run_ids.append(run.id)
        logger.warning(
            "ai_workflow_stale_marked_failed",
            extra={
                "event": "ai_workflow_stale_marked_failed",
                "run_id": run.id,
                "customer_id": run.customer_id,
                "provider_name": run.provider_name,
                "actor_user_id": getattr(current_user, "id", None),
            },
        )
    db.commit()
    return {
        "marked_failed": len(run_ids),
        "run_ids": run_ids,
        "stale_after_seconds": stale_after_seconds,
    }
