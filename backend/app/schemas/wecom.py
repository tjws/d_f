from datetime import datetime

from pydantic import BaseModel, Field


class WeComMockLogin(BaseModel):
    """Mock 企业微信登录请求。"""

    code: str = Field(min_length=1, max_length=100)


class WeComMockCallback(BaseModel):
    """本地 Mock 企业微信回调的统一请求模型。"""

    event_id: str = Field(min_length=1, max_length=200)
    event_type: str = Field(min_length=1, max_length=100)
    userid: str = Field(min_length=1, max_length=100)
    username: str | None = Field(default=None, max_length=50)
    name: str | None = Field(default=None, max_length=100)
    customer_id: int | None = None
    wecom_message_id: str | None = Field(default=None, max_length=200)
    direction: str | None = Field(default=None, max_length=20)
    message_type: str | None = Field(default=None, max_length=30)
    content: str | None = Field(default=None, max_length=10000)
    media_object_key: str | None = Field(default=None, max_length=500)
    sent_at: datetime | None = None
