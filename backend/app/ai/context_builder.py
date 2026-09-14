from datetime import datetime

from sqlalchemy.orm import Session

from app.core.crypto import decrypt_text
from app.dao.chat_message_dao import ChatMessageDAO
from app.dao.customer_dao import CustomerDAO
from app.dao.customer_profile_dao import CustomerProfileDAO
from app.dao.timeline_event_dao import TimelineEventDAO
from app.services.chat_message_service import mask_sensitive_text


customer_dao = CustomerDAO()
profile_dao = CustomerProfileDAO()
chat_message_dao = ChatMessageDAO()
timeline_event_dao = TimelineEventDAO()


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def build_customer_context(db: Session, customer_id: int) -> dict[str, object]:
    """读取并脱敏客户资料，生成供 AI 节点使用的上下文。"""

    customer = customer_dao.get_by_id(db, customer_id)
    if customer is None:
        raise ValueError(f"customer {customer_id} not found")

    confirmed_profile = profile_dao.get_current_confirmed(db, customer_id)
    messages = chat_message_dao.list_by_customer(db, customer_id)
    timeline_events = timeline_event_dao.list_by_customer(db, customer_id)

    return {
        "customer": {
            "id": customer.id,
            "name": customer.name,
            # 手机号只保留脱敏版本，禁止把原始号码送入 AI 上下文。
            "phone": mask_sensitive_text(customer.phone),
            "student_name": customer.student_name,
            "grade": customer.grade,
            "interested_subject": customer.interested_subject,
            "stage": customer.stage,
            "source": customer.source,
            "remark": mask_sensitive_text(customer.remark or ""),
        },
        # 只有人工确认过的画像才能作为后续建议的可信上下文。
        "confirmed_profile": (
            {
                "id": confirmed_profile.id,
                "version": confirmed_profile.version,
                "dimensions": confirmed_profile.dimensions_json,
                "evidence": confirmed_profile.evidence_json,
            }
            if confirmed_profile is not None
            else None
        ),
        "messages": [
            {
                "direction": message.direction,
                "message_type": message.message_type,
                "content": message.content_masked,
                "sent_at": _iso(message.sent_at),
            }
            for message in messages[:20]
        ],
        "timeline_events": [
            {
                "event_type": event.event_type,
                "summary": decrypt_text(event.summary_encrypted),
                "source": event.source,
                "occurred_at": _iso(event.occurred_at),
            }
            for event in timeline_events[:20]
        ],
    }
