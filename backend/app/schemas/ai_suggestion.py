from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AISuggestionStatus(str, Enum):
    DRAFT = "draft"
    EDITED = "edited"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"


class AISuggestionUpdate(BaseModel):
    """人工编辑建议正文；发送动作不属于本接口。"""

    content: dict[str, Any] = Field(min_length=1)


class AISuggestionRead(BaseModel):
    id: int
    customer_id: int
    user_id: int | None
    profile_id: int | None
    suggestion_type: str
    content: dict[str, Any]
    edited_content: dict[str, Any] | None
    evidence: list[dict[str, Any]]
    evidence_level: str
    status: AISuggestionStatus
    model_name: str
    model_version: str
    prompt_version: str
    decided_by: int | None
    decided_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
