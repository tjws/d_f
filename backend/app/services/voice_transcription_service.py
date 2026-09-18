from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.crypto import encrypt_text
from app.dao.chat_message_dao import ChatMessageDAO
from app.dao.timeline_event_dao import TimelineEventDAO
from app.integrations.transcription.factory import get_transcription_provider
from app.models.chat_message import ChatMessage
from app.models.timeline_event import TimelineEvent
from app.models.user import User
from app.services.audit_log_service import append_audit_log
from app.services.chat_message_service import mask_sensitive_text, to_chat_message_read
from app.services.customer_service import get_customer_or_404


chat_message_dao = ChatMessageDAO()
timeline_event_dao = TimelineEventDAO()
timeline_dao = timeline_event_dao


def transcribe_voice_message(db: Session, customer_id: int, message_id: int, actor: User):
    """只处理已有语音消息；重复请求直接返回已有转写，避免重复时间线。"""

    get_customer_or_404(db, customer_id, actor, "update")
    message = db.scalar(
        select(ChatMessage).where(
            ChatMessage.id == message_id,
            ChatMessage.customer_id == customer_id,
        )
    )
    if message is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="语音消息不存在")
    if message.message_type != "voice":
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="只有语音消息可以转写")
    if message.content_encrypted is not None:
        return message
    if not message.media_object_key:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="语音消息缺少媒体对象引用")

    transcript = get_transcription_provider().transcribe(message.media_object_key).strip()
    if not transcript:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="语音转写未返回文本")
    message.content_encrypted = encrypt_text(transcript)
    message.content_masked = mask_sensitive_text(transcript)
    timeline_dao.add(
        db,
        TimelineEvent(
            customer_id=customer_id,
            operator_id=actor.id,
            occurred_at=datetime.now(timezone.utc),
            event_type="voice_transcribed",
            summary_encrypted=encrypt_text(message.content_masked),
            source="system",
            reference_type="chat_message",
            reference_id=str(message.id),
        ),
    )
    append_audit_log(db, actor, "customer.voice_transcribed", "chat_message", str(message.id), {"provider": "mock", "content_length": len(transcript)})
    db.commit()
    db.refresh(message)
    return message
