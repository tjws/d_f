from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TimelineEventCreate(BaseModel):
    """创建人工时间线事件时允许提交的字段。"""

    event_type: str = Field(
        min_length=1,
        max_length=50,
    )

    # 接口接收明文，保存到数据库前由服务层加密。
    summary: str = Field(
        min_length=1,
        max_length=5000,
    )

    occurred_at: datetime | None = None

    reference_type: str | None = Field(
        default=None,
        max_length=50,
    )

    reference_id: str | None = Field(
        default=None,
        max_length=100,
    )


class TimelineEventRead(BaseModel):
    """返回给前端的时间线事件。"""

    id: int
    customer_id: int
    operator_id: int | None
    occurred_at: datetime
    event_type: str
    summary: str
    source: str
    reference_type: str | None
    reference_id: str | None
    created_at: datetime

    # 允许 Pydantic 从 SQLAlchemy 模型对象读取字段。
    model_config = ConfigDict(from_attributes=True)