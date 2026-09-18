from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class AIWorkflowRunAdminRead(BaseModel):
    id: int
    customer_id: int
    actor_user_id: int | None
    goal: str
    provider_name: str
    status: Literal["queued", "running", "paused", "waiting_human", "succeeded", "failed"]
    attempt_count: int
    error_code: str | None
    next_action: str | None
    suggestion_count: int
    created_at: datetime
    started_at: datetime | None
    heartbeat_at: datetime | None
    finished_at: datetime | None
    max_attempts: int
    retryable: bool


class AIWorkflowRunAdminList(BaseModel):
    items: list[AIWorkflowRunAdminRead]
    total: int


class AIWorkflowRecoveryRequest(BaseModel):
    # 该接口只允许明确确认，避免误把仍在执行的任务标记为失败。
    confirm: bool = Field(default=False)
    stale_after_seconds: int = Field(default=120, ge=30, le=86400)
    limit: int = Field(default=50, ge=1, le=200)


class AIWorkflowRecoveryRead(BaseModel):
    marked_failed: int
    run_ids: list[int]
    stale_after_seconds: int
