from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SystemSettingUpdate(BaseModel):
    value: Any
    description: str | None = Field(default=None, max_length=500)


class SystemSettingRead(BaseModel):
    id: int
    key: str
    value: Any
    scope_type: str
    scope_id: int | None
    description: str | None
    updated_by: int | None
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
