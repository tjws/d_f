from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class OrganizationCreate(BaseModel):
    """创建组织时接收的数据。"""

    name: str = Field(min_length=1, max_length=100)
    type: str = Field(min_length=1, max_length=30)
    parent_id: int | None = None


class OrganizationRead(BaseModel):
    """返回给前端的组织数据。"""

    id: int
    parent_id: int | None
    name: str
    type: str
    path: str | None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
