import asyncio
import json
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import SessionLocal, get_db
from app.models.user import User
from app.schemas.ai_workflow import AIWorkflowRetryRequest, AIWorkflowRunRead, AIWorkflowRunRequest
from app.services.ai_workflow_service import (
    get_customer_ai_workflow_run,
    run_customer_ai_workflow,
    retry_customer_ai_workflow,
)


router = APIRouter(
    prefix="/customers/{customer_id}/ai-workflow",
    tags=["ai-workflow"],
)


@router.post("", response_model=AIWorkflowRunRead)
def run_ai_workflow(
    customer_id: int,
    payload: AIWorkflowRunRequest | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return run_customer_ai_workflow(
        db,
        customer_id,
        current_user,
        payload.goal if payload is not None else "reply",
        payload.idempotency_key if payload is not None else None,
    )


@router.get("/{run_id}", response_model=AIWorkflowRunRead)
def get_ai_workflow_run(
    customer_id: int,
    run_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_customer_ai_workflow_run(db, customer_id, run_id, current_user)


@router.get("/{run_id}/events")
async def stream_ai_workflow_events(
    customer_id: int,
    run_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """以 SSE 推送工作流状态；JWT 通过 Authorization 头传入，不放进 URL。"""

    # 先在请求线程完成一次数据权限校验，避免把任务 ID 当成越权入口。
    get_customer_ai_workflow_run(db, customer_id, run_id, current_user)

    async def event_stream():
        last_payload = ""
        deadline = datetime.now(timezone.utc) + timedelta(seconds=120)
        while datetime.now(timezone.utc) < deadline:
            with SessionLocal() as stream_db:
                payload = get_customer_ai_workflow_run(
                    stream_db, customer_id, run_id, current_user
                )
            encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
            if encoded != last_payload:
                last_payload = encoded
                yield f"event: workflow\ndata: {encoded}\n\n"
            if payload["status"] not in {"queued", "running"}:
                yield f"event: done\ndata: {encoded}\n\n"
                return
            # 注释心跳让代理保持连接，不携带业务数据。
            yield ": heartbeat\n\n"
            await asyncio.sleep(1)

        timeout_payload = {"run_id": run_id, "customer_id": customer_id, "status": "timeout"}
        yield f"event: timeout\ndata: {json.dumps(timeout_payload)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/{run_id}/retry", response_model=AIWorkflowRunRead)
def retry_ai_workflow(
    customer_id: int,
    run_id: int,
    payload: AIWorkflowRetryRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return retry_customer_ai_workflow(db, customer_id, run_id, current_user, payload.confirm)
