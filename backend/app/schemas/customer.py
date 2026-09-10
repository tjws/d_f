from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class CustomerStage(str, Enum):
    NEW = "new"
    FOLLOWING_UP = "following_up"
    CONVERTED = "converted"
    LOST = "lost"


class CustomerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    phone: str = Field(min_length=6, max_length=30)

    student_name: str | None = Field(default=None, max_length=50)
    grade: str | None = Field(default=None, max_length=30)
    interested_subject: str | None = Field(default=None, max_length=50)

    stage: CustomerStage = CustomerStage.NEW
    source: str | None = Field(default=None, max_length=50)
    remark: str | None = Field(default=None, max_length=500)
    next_follow_up_at: datetime | None = None

class CustomerUpdate(BaseModel):
    """客户修改模型：所有字段都是可选的，只修改传入的字段。"""

    name: str | None = Field(default=None, min_length=1, max_length=50)
    phone: str | None = Field(default=None, min_length=6, max_length=30)
    student_name: str | None = Field(default=None, max_length=50)
    grade: str | None = Field(default=None, max_length=30)
    interested_subject: str | None = Field(default=None, max_length=50)
    stage: CustomerStage | None = None
    source: str | None = Field(default=None, max_length=50)
    remark: str | None = Field(default=None, max_length=500)
    next_follow_up_at: datetime | None = None

class CustomerRead(CustomerCreate):
    """返回给前端的客户模型。"""

    id: int
    created_at: datetime
    updated_at: datetime

    # 允许 Pydantic 直接读取 SQLAlchemy 模型对象的属性。
    model_config = ConfigDict(from_attributes=True)

class CustomerListResponse(BaseModel):
    """客户列表响应，包含数据和分页信息。"""

    items: list[CustomerRead]
    total: int
    page: int
    page_size: int