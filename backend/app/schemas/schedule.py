from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ScheduleUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    due_at: datetime | None = None
    priority: str | None = Field(default=None, pattern="^(low|normal|high)$")


class ScheduleRead(BaseModel):
    id: int
    customer_id: int
    user_id: int | None
    suggestion_id: int | None
    title: str
    description: str | None
    due_at: datetime
    priority: str
    source: str
    status: str
    evidence: list[dict[str, Any]]
    confirmed_by: int | None
    confirmed_at: datetime | None
    wecom_calendar_id: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
