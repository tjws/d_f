from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TagRead(BaseModel):
    id: int
    key: str
    name: str
    category: str
    description: str | None
    color: str | None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CustomerTagRead(BaseModel):
    id: int
    customer_id: int
    tag: TagRead
    source: str
    status: str
    evidence: list[dict]
    created_by: int | None
    confirmed_by: int | None
    created_at: datetime
    confirmed_at: datetime | None
