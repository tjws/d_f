from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ChatMessageDirection(str, Enum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"


class ChatMessageType(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    VOICE = "voice"
    FILE = "file"


class ChatMessageCreate(BaseModel):
    """本地 Mock 消息入口允许提交的字段。"""

    wecom_message_id: str = Field(min_length=1, max_length=200)
    direction: ChatMessageDirection
    message_type: ChatMessageType = ChatMessageType.TEXT
    content: str | None = Field(default=None, max_length=10000)
    media_object_key: str | None = Field(default=None, max_length=500)
    sent_at: datetime | None = None

    @model_validator(mode="after")
    def validate_content(self):
        if self.message_type == ChatMessageType.TEXT and not self.content:
            raise ValueError("文本消息必须提供 content")
        return self


class ChatMessageRead(BaseModel):
    id: int
    customer_id: int
    user_id: int | None
    wecom_message_id: str
    direction: ChatMessageDirection
    message_type: ChatMessageType
    content: str | None
    content_masked: str | None
    media_object_key: str | None
    sent_at: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
