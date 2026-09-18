from sqlalchemy.orm import Session

from app.dao.chat_message_dao import ChatMessageDAO
from app.dao.timeline_event_dao import TimelineEventDAO
from app.models.user import User
from app.schemas.sidebar_sync import SidebarSyncRead
from app.services.chat_message_service import to_chat_message_read
from app.services.customer_service import get_customer_or_404
from app.services.timeline_event_service import to_timeline_event_read


chat_message_dao = ChatMessageDAO()
timeline_event_dao = TimelineEventDAO()


def get_sidebar_sync(
    db: Session,
    customer_id: int,
    current_user: User,
    after_message_id: int,
    after_timeline_id: int,
) -> SidebarSyncRead:
    """校验客户数据权限后，只返回两个游标之后的新消息和时间线。"""

    get_customer_or_404(db, customer_id, current_user, "read")
    messages = chat_message_dao.list_after_id(db, customer_id, after_message_id)
    timeline_events = timeline_event_dao.list_after_id(db, customer_id, after_timeline_id)
    return SidebarSyncRead(
        messages=[to_chat_message_read(message) for message in messages],
        timeline_events=[to_timeline_event_read(event) for event in timeline_events],
        next_message_id=max([after_message_id, *(message.id for message in messages)]),
        next_timeline_id=max([after_timeline_id, *(event.id for event in timeline_events)]),
    )
