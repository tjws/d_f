from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


ScriptStatus = Literal["draft", "pending_review", "published", "disabled"]


class SalesScriptCreate(BaseModel):
    scene: str = Field(min_length=1, max_length=50)
    customer_stage: str | None = Field(default=None, max_length=30)
    objection_type: str | None = Field(default=None, max_length=50)
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1, max_length=10000)
    tone: str | None = Field(default=None, max_length=30)


class SalesScriptUpdate(BaseModel):
    scene: str | None = Field(default=None, min_length=1, max_length=50)
    customer_stage: str | None = Field(default=None, max_length=30)
    objection_type: str | None = Field(default=None, max_length=50)
    title: str | None = Field(default=None, min_length=1, max_length=200)
    content: str | None = Field(default=None, min_length=1, max_length=10000)
    tone: str | None = Field(default=None, max_length=30)
    status: ScriptStatus | None = None


class SalesScriptRead(BaseModel):
    id: int
    scene: str
    customer_stage: str | None
    objection_type: str | None
    title: str
    content: str
    tone: str | None
    status: str
    version: int
    created_by: int | None
    approved_by: int | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
