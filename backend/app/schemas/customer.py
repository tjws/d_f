from enum import Enum

from pydantic import BaseModel, Field


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