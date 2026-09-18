from typing import Literal

from pydantic import BaseModel, Field


AIWorkflowGoal = Literal["profile", "reply", "tag", "schedule"]


class AIWorkflowRunRequest(BaseModel):
    """调用方明确选择一类建议，默认兼容原有的回复建议行为。"""

    goal: AIWorkflowGoal = "reply"
    # 前端重试或网络重发时携带同一个键，后端会复用原运行记录。
    idempotency_key: str | None = Field(default=None, min_length=8, max_length=100, pattern=r"^[A-Za-z0-9._:-]+$")


class AIWorkflowRunRead(BaseModel):
    """一次 LangGraph 运行的结果；建议仍需人工确认。"""

    customer_id: int
    run_id: int | None = None
    status: Literal["queued", "running", "paused", "waiting_human", "failed"]
    suggestion_ids: list[int] = Field(default_factory=list)
    customer_tag_ids: list[int] = Field(default_factory=list)
    profile_id: int | None = None
    next_action: Literal[
        "confirm_profile",
        "review_reply",
        "confirm_tags",
        "review_schedule",
        "resume_agent",
    ] | None = None
    error: str | None = None
    attempt_count: int = 0
    max_attempts: int = 3
    retryable: bool = False


class AIWorkflowRetryRequest(BaseModel):
    """显式人工重试请求；不会由 Worker 自动循环重试。"""

    confirm: bool = Field(default=False, description="必须明确确认本次可能再次调用模型")
