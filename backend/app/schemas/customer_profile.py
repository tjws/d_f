from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CustomerProfileStatus(str, Enum):
    DRAFT = "draft"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    ARCHIVED = "archived"


class CustomerProfileUpdate(BaseModel):
    """人工只能编辑画像维度，不允许修改版本和确认信息。"""

    dimensions: dict[str, Any] = Field(min_length=1)


class CustomerProfileRead(BaseModel):
    id: int
    customer_id: int
    version: int
    status: CustomerProfileStatus
    dimensions: dict[str, Any]
    evidence: list[dict[str, Any]]
    model_name: str
    model_version: str
    prompt_version: str
    confirmed_by: int | None
    confirmed_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
