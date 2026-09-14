from typing import Any

from app.core.crypto import decrypt_text
from app.models.chat_message import ChatMessage
from app.models.customer import Customer
from app.models.student import Student
from app.models.timeline_event import TimelineEvent
from app.services.chat_message_service import mask_sensitive_text


def _safe_decrypt(value: str | None) -> str | None:
    if value is None:
        return None
    return mask_sensitive_text(decrypt_text(value))


def generate_mock_profile(customer: Customer, students: list[Student], messages: list[ChatMessage], events: list[TimelineEvent]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """用可预测规则生成画像草稿，为后续模型替换保留统一输出契约。"""
    student_facts = []
    evidence = []
    for student in students:
        fact = {
            "grade": student.grade,
            "gender": student.gender,
            "school": _safe_decrypt(student.school_encrypted),
            "subjects": student.subjects_json or {},
        }
        student_facts.append(fact)
        evidence.append({"source_type": "student", "source_id": str(student.id), "fact": fact})

    message_facts = []
    for message in messages[:20]:
        fact = {"direction": message.direction, "message_type": message.message_type, "content": message.content_masked}
        message_facts.append(fact)
        evidence.append({"source_type": "chat_message", "source_id": str(message.id), "fact": fact})

    for event in events[:20]:
        fact = {"event_type": event.event_type, "summary": _safe_decrypt(event.summary_encrypted), "occurred_at": event.occurred_at.isoformat()}
        evidence.append({"source_type": "timeline_event", "source_id": str(event.id), "fact": fact})

    dimensions = {
        "customer_stage": customer.stage,
        "interested_subject": customer.interested_subject,
        "student_count": len(students),
        "students": student_facts,
        "recent_message_count": len(messages),
        "recent_event_count": len(events),
        "next_action": "由销售顾问结合证据确认下一次沟通重点",
    }
    return dimensions, evidence
