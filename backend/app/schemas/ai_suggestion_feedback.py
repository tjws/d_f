from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


FeedbackAction = Literal["accepted", "edited", "rejected", "incorrect_reasoning", "missing_information", "not_useful"]
AgentFeedbackAction = Literal["incorrect_reasoning", "missing_information", "not_useful"]


class AISuggestionFeedbackRead(BaseModel):
    id: int
    suggestion_id: int | None
    customer_id: int
    target_type: str
    target_id: str
    actor_user_id: int | None
    action: FeedbackAction
    edited_content: dict[str, Any] | None
    note: str | None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class AgentFeedbackCreate(BaseModel):
    action: AgentFeedbackAction
    note: str | None = Field(default=None, max_length=300)


class AgentFeedbackRead(BaseModel):
    id: int
    suggestion_id: int | None
    customer_id: int
    target_type: str
    target_id: str
    actor_user_id: int | None
    action: AgentFeedbackAction
    note: str | None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
