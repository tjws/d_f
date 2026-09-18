from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


AIRolloutMode = Literal["all", "pilot"]
AIRolloutSegment = Literal["new", "experienced", "unclassified"]
AIRolloutMembershipStatus = Literal["active", "removed"]


class AIRolloutModeUpdate(BaseModel):
    mode: AIRolloutMode


class AIRolloutMemberCreate(BaseModel):
    user_id: int = Field(gt=0)
    segment: AIRolloutSegment = "unclassified"


class AIRolloutMemberRead(BaseModel):
    id: int
    user_id: int
    username: str
    full_name: str | None
    role: str
    segment: AIRolloutSegment
    status: AIRolloutMembershipStatus
    added_by: int | None
    started_at: datetime
    ended_at: datetime | None
    created_at: datetime


class AIRolloutReportRead(BaseModel):
    id: int
    report_date: date
    cohort: str
    metrics: dict[str, Any]
    generated_by: int | None
    created_at: datetime
    updated_at: datetime


class AIRolloutConfigRead(BaseModel):
    mode: AIRolloutMode
    active_member_count: int
    max_member_count: int

