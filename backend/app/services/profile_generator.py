from typing import Any

from app.ai.providers import get_profile_provider
from app.models.chat_message import ChatMessage
from app.models.customer import Customer
from app.models.student import Student
from app.models.timeline_event import TimelineEvent


def generate_mock_profile(
    customer: Customer,
    students: list[Student],
    messages: list[ChatMessage],
    events: list[TimelineEvent],
) -> tuple[dict[str, Any], list[dict[str, Any]], str, str]:
    """保留旧服务函数签名，并委托给统一的 MockProfileProvider。"""

    payload = get_profile_provider().generate(
        {
            "customer": {
                "stage": customer.stage,
                "interested_subject": customer.interested_subject,
            },
            "students": [
                {
                    "id": student.id,
                    "grade": student.grade,
                    "gender": student.gender,
                    "school_encrypted": student.school_encrypted,
                    "subjects": student.subjects_json,
                }
                for student in students
            ],
            "messages": [
                {
                    "id": message.id,
                    "direction": message.direction,
                    "message_type": message.message_type,
                    "content_masked": message.content_masked,
                }
                for message in messages
            ],
            "timeline_events": [
                {
                    "id": event.id,
                    "event_type": event.event_type,
                    "summary_encrypted": event.summary_encrypted,
                    "occurred_at": event.occurred_at.isoformat(),
                }
                for event in events
            ],
        }
    )
    return (
        payload["dimensions"],
        payload["evidence"],
        payload["model_name"],
        payload["model_version"],
    )
