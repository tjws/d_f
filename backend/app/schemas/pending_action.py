"""统一待处理工作台的 API 契约。"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


PendingActionType = Literal["profile", "reply", "tag", "schedule"]
PendingActionDecisionType = Literal["accepted", "edited", "rejected"]


class PendingActionRead(BaseModel):
    """一个待人工确认的项目；不复制完整客户敏感信息或 AI 原文。"""

    id: str
    resource_id: int
    action_type: PendingActionType
    customer_id: int
    customer_name: str
    customer_stage: str
    status: str
    title: str
    summary: str
    created_at: datetime


class PendingActionListRead(BaseModel):
    items: list[PendingActionRead] = Field(default_factory=list)
    total: int = 0


class PendingActionDecision(BaseModel):
    action: PendingActionDecisionType
    content: dict | None = None


class PendingActionDecisionRead(BaseModel):
    action_type: PendingActionType
    resource_id: int
    action: PendingActionDecisionType
    status: str
    closed: bool
