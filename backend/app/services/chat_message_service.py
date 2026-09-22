import re
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.crypto import decrypt_text, encrypt_text
from app.dao.chat_message_dao import ChatMessageDAO
from app.dao.timeline_event_dao import TimelineEventDAO
from app.models.chat_message import ChatMessage
from app.models.ai_suggestion import AISuggestion
from app.models.timeline_event import TimelineEvent
from app.models.user import User
from app.schemas.chat_message import ChatMessageCreate
from app.services.ai_suggestion_feedback_service import record_feedback
from app.services.audit_log_service import append_audit_log


class ChatMessageConflict(ValueError):
    """表示同一个外部消息编号被绑定到了其他客户。"""


_PHONE_PATTERN = re.compile(r"(?<!\d)1\d{10}(?!\d)")
chat_message_dao = ChatMessageDAO()
timeline_event_dao = TimelineEventDAO()


def _normalized_message_text(value: str) -> str:
    """比较人工发送文本时忽略空白差异，便于保留建议到消息的追溯关系。"""

    return " ".join(value.split())


def _infer_accepted_reply_suggestion(
    db: Session,
    customer_id: int,
    content: str | None,
) -> AISuggestion | None:
    """销售手动复制已接受话术时，仍尝试关联到唯一的同文建议。

    这是“建议 -> 人工发送”审计链的兜底，不会接受草稿、不会改写消息，且只在
    内容与已接受建议完全一致时才生效。
    """

    if not content:
        return None
    expected = _normalized_message_text(content)
    candidates = db.scalars(
        select(AISuggestion)
        .where(
            AISuggestion.customer_id == customer_id,
            AISuggestion.suggestion_type == "reply",
            AISuggestion.status == "accepted",
        )
        .order_by(AISuggestion.decided_at.desc(), AISuggestion.id.desc())
    ).all()
    for candidate in candidates:
        payload = candidate.edited_content_json or candidate.content_json
        text = payload.get("text") if isinstance(payload, dict) else None
        if isinstance(text, str) and _normalized_message_text(text) == expected:
            return candidate
    return None


def mask_sensitive_text(value: str) -> str:
    """对手机号做最小脱敏，供列表展示和 AI 输入使用。"""

    return _PHONE_PATTERN.sub(
        lambda match: f"{match.group(0)[:3]}****{match.group(0)[-4:]}",
        value,
    )


def to_chat_message_read(message: ChatMessage):
    """将数据库消息转换成不暴露加密字段的响应对象。"""

    from app.schemas.chat_message import ChatMessageRead

    return ChatMessageRead(
        id=message.id,
        customer_id=message.customer_id,
        user_id=message.user_id,
        suggestion_id=message.suggestion_id,
        wecom_message_id=message.wecom_message_id,
        direction=message.direction,
        message_type=message.message_type,
        content=(
            decrypt_text(message.content_encrypted)
            if message.content_encrypted is not None
            else None
        ),
        content_masked=message.content_masked,
        media_object_key=message.media_object_key,
        sent_at=message.sent_at,
        created_at=message.created_at,
    )


def create_chat_message(
    db: Session,
    customer_id: int,
    current_user: User,
    payload: ChatMessageCreate,
) -> tuple[ChatMessage, bool]:
    """写入消息并在同一事务中创建时间线事件。"""

    existing = chat_message_dao.get_by_wecom_message_id(db, payload.wecom_message_id)
    if existing is not None:
        if existing.customer_id != customer_id:
            raise ChatMessageConflict("外部消息编号已绑定其他客户")
        return existing, False

    sent_at = payload.sent_at or datetime.now(timezone.utc)
    content_masked = (
        mask_sensitive_text(payload.content)
        if payload.content is not None
        else None
    )

    suggestion = None
    resolved_suggestion_id = payload.suggestion_id
    if resolved_suggestion_id is None and payload.direction.value == "outbound":
        suggestion = _infer_accepted_reply_suggestion(db, customer_id, payload.content)
        resolved_suggestion_id = suggestion.id if suggestion is not None else None
    if resolved_suggestion_id is not None:
        if payload.direction.value != "outbound":
            raise ChatMessageConflict("AI suggestion links are only valid for outbound messages")
        suggestion = suggestion or db.get(AISuggestion, resolved_suggestion_id)
        if suggestion is None or suggestion.customer_id != customer_id:
            raise ChatMessageConflict("AI suggestion does not belong to this customer")
        if suggestion.suggestion_type != "reply" or suggestion.status != "accepted":
            raise ChatMessageConflict("Only an accepted reply suggestion can be sent")

    message = ChatMessage(
        customer_id=customer_id,
        user_id=current_user.id,
        suggestion_id=resolved_suggestion_id,
        wecom_message_id=payload.wecom_message_id,
        direction=payload.direction.value,
        message_type=payload.message_type.value,
        content_encrypted=(
            encrypt_text(payload.content)
            if payload.content is not None
            else None
        ),
        content_masked=content_masked,
        media_object_key=payload.media_object_key,
        sent_at=sent_at,
    )
    chat_message_dao.add(db, message)
    db.flush()

    timeline_summary = content_masked or (
        f"收到一条 {payload.message_type.value} 消息"
    )
    timeline_event_dao.add(db, TimelineEvent(
            customer_id=customer_id,
            operator_id=current_user.id,
            occurred_at=sent_at,
            event_type="wecom_message",
            summary_encrypted=encrypt_text(timeline_summary),
            source="wecom",
            reference_type="chat_message",
            reference_id=str(message.id),
        ))

    if suggestion is not None:
        reviewed_content = suggestion.edited_content_json or suggestion.content_json
        sent_content = {"text": payload.content}
        if reviewed_content != sent_content:
            record_feedback(db, suggestion, current_user, "edited", sent_content)
        append_audit_log(
            db,
            current_user,
            "customer.ai_reply_sent",
            "ai_suggestion",
            str(suggestion.id),
            {"sent": True, "edited_before_send": reviewed_content != sent_content},
        )

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = chat_message_dao.get_by_wecom_message_id(db, payload.wecom_message_id)
        if existing is not None and existing.customer_id == customer_id:
            return existing, False
        raise ChatMessageConflict("外部消息编号已绑定其他客户") from None

    db.refresh(message)
    return message, True


def list_chat_messages(
    db: Session,
    customer_id: int,
) -> list[ChatMessage]:
    """按发送时间倒序读取客户聊天消息。"""

    return chat_message_dao.list_by_customer(db, customer_id)
