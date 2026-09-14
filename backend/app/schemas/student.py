from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class StudentCreate(BaseModel):
    """学生接口接收明文资料，写入数据库前会完成加密。"""

    name: str = Field(min_length=1, max_length=100)
    gender: str | None = Field(default=None, max_length=30)
    grade: str | None = Field(default=None, max_length=30)
    school: str | None = Field(default=None, max_length=200)
    birth_date: date | None = None
    subjects: dict[str, Any] | None = None


class StudentRead(BaseModel):
    """学生响应只暴露业务字段，不暴露数据库密文。"""

    id: int
    customer_id: int
    name: str
    gender: str | None
    grade: str | None
    school: str | None
    birth_date: date | None
    subjects: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
