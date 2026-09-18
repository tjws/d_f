from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


TicketStatus = Literal["open", "in_progress", "resolved", "closed"]


class ServiceTicketCreate(BaseModel):
    external_ticket_id: str = Field(min_length=1, max_length=100)
    type: str = Field(default="general", min_length=1, max_length=50)
    summary: str = Field(min_length=1, max_length=5000)
    status: TicketStatus = "open"
    opened_at: datetime | None = None


class ServiceTicketUpdate(BaseModel):
    type: str | None = Field(default=None, min_length=1, max_length=50)
    summary: str | None = Field(default=None, min_length=1, max_length=5000)
    status: TicketStatus | None = None


class ServiceTicketRead(BaseModel):
    id: int
    external_ticket_id: str
    customer_id: int
    type: str
    status: str
    summary: str
    opened_at: datetime
    closed_at: datetime | None
    raw_snapshot: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
