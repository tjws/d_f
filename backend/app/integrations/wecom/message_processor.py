from app.dao.customer_dao import CustomerDAO
from app.dao.user_dao import UserDAO
from app.db.session import SessionLocal
from app.schemas.chat_message import (
    ChatMessageCreate,
    ChatMessageDirection,
    ChatMessageType,
)
from app.schemas.wecom import WeComMockCallback
from app.services.chat_message_service import create_chat_message


def process_mock_chat_message(payload: WeComMockCallback) -> None:
    """将已验签的 Mock 回调转换为内部聊天消息。"""

    required_fields = (
        payload.customer_id,
        payload.wecom_message_id,
        payload.direction,
        payload.message_type,
    )
    if any(value is None for value in required_fields):
        raise ValueError("chat_message 回调缺少必要字段")

    try:
        direction = ChatMessageDirection(payload.direction)
        message_type = ChatMessageType(payload.message_type)
    except ValueError as exc:
        raise ValueError("chat_message 的 direction 或 message_type 无效") from exc

    with SessionLocal() as db:
        user = UserDAO().get_by_wecom_userid(db, payload.userid)
        if user is None or not user.is_active:
            raise ValueError("chat_message 回调对应的企业微信用户不存在")

        customer = CustomerDAO().get_by_id(db, payload.customer_id)
        if customer is None:
            raise ValueError("chat_message 回调对应的客户不存在")

        chat_payload = ChatMessageCreate(
            wecom_message_id=payload.wecom_message_id,
            direction=direction,
            message_type=message_type,
            content=payload.content,
            media_object_key=payload.media_object_key,
            sent_at=payload.sent_at,
        )
        create_chat_message(db, customer.id, user, chat_payload)
