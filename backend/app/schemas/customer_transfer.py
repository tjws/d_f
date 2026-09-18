from datetime import datetime

from pydantic import BaseModel, Field


class CustomerTransferCreate(BaseModel):
    to_user_id: int = Field(gt=0)
    reason: str | None = Field(default=None, max_length=500)


class CustomerTransferRead(BaseModel):
    id: int
    customer_id: int
    from_user_id: int | None
    to_user_id: int | None
    operator_id: int | None
    reason: str | None
    created_at: datetime
