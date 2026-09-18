from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


TagStatus = Literal["active", "inactive"]


class AdminTagCreate(BaseModel):
    key: str = Field(min_length=2, max_length=80, pattern=r"^[a-z0-9][a-z0-9_-]*$")
    name: str = Field(min_length=1, max_length=50)
    category: str = Field(min_length=1, max_length=50)
    description: str | None = Field(default=None, max_length=500)
    color: str | None = Field(default=None, max_length=20)
    status: TagStatus = "active"


class AdminTagUpdate(BaseModel):
    key: str | None = Field(default=None, min_length=2, max_length=80, pattern=r"^[a-z0-9][a-z0-9_-]*$")
    name: str | None = Field(default=None, min_length=1, max_length=50)
    category: str | None = Field(default=None, min_length=1, max_length=50)
    description: str | None = Field(default=None, max_length=500)
    color: str | None = Field(default=None, max_length=20)
    status: TagStatus | None = None


class AdminTagRead(BaseModel):
    id: int
    key: str
    name: str
    category: str
    description: str | None
    color: str | None
    status: str
    assignment_count: int
    customer_count: int
    suggested_count: int
    confirmed_count: int
    rejected_count: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
