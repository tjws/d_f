"""“我的待办”跨 AI 审阅和正式日程的 API 契约。"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


MyWorkBucket = Literal["review", "overdue", "today", "upcoming", "historical"]
MyWorkItemType = Literal["ai_review", "schedule"]
MyWorkActionType = Literal["profile", "reply", "tag", "schedule"]


class MyWorkItemRead(BaseModel):
    id: str
    resource_id: int
    item_type: MyWorkItemType
    bucket: MyWorkBucket
    action_type: MyWorkActionType | None = None
    status: str | None = None
    customer_id: int
    customer_name: str
    customer_stage: str
    title: str
    summary: str
    priority: str | None = None
    due_at: datetime | None = None
    created_at: datetime


class MyWorkSummaryRead(BaseModel):
    review: int = 0
    overdue: int = 0
    today: int = 0
    upcoming: int = 0
    # 历史草稿只供回溯和关闭，不计入销售当天的核心待办。
    historical: int = 0


class MyWorkRead(BaseModel):
    summary: MyWorkSummaryRead
    items: list[MyWorkItemRead] = Field(default_factory=list)
