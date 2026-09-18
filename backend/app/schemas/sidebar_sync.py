from pydantic import BaseModel

from app.schemas.chat_message import ChatMessageRead
from app.schemas.timeline_event import TimelineEventRead


class SidebarSyncRead(BaseModel):
    """侧边栏增量同步结果；游标使用数据库自增 ID。"""

    messages: list[ChatMessageRead]
    timeline_events: list[TimelineEventRead]
    next_message_id: int
    next_timeline_id: int
