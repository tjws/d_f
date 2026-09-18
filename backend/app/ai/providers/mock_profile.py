from app.ai.providers.base import ProfileSuggestionPayload
from app.core.crypto import decrypt_text
from app.services.chat_message_service import mask_sensitive_text


def _safe_decrypt(value: str | None) -> str | None:
    if value is None:
        return None
    return mask_sensitive_text(decrypt_text(value))


class MockProfileProvider:
    """本地规则画像 Provider；只输出脱敏字段，不调用外部模型。"""

    def generate(self, context: dict[str, object]) -> ProfileSuggestionPayload:
        customer = context.get("customer")
        students = context.get("students", [])
        messages = context.get("messages", [])
        events = context.get("timeline_events", [])

        if not isinstance(customer, dict):
            raise ValueError("customer context is required")
        if not isinstance(students, list) or not isinstance(messages, list) or not isinstance(events, list):
            raise ValueError("profile context collections must be lists")

        student_facts: list[dict[str, object]] = []
        evidence: list[dict[str, object]] = []
        for student in students:
            if not isinstance(student, dict):
                continue
            fact = {
                "grade": student.get("grade"),
                "gender": student.get("gender"),
                # Graph 上下文已经脱敏；旧服务入口仍可能提供加密字段，兼容两种输入。
                "school": student.get("school") or _safe_decrypt(student.get("school_encrypted")),
                "subjects": student.get("subjects") or {},
            }
            student_facts.append(fact)
            evidence.append(
                {
                    "source_type": "student",
                    "source_id": str(student.get("id", "")),
                    "fact": fact,
                }
            )

        message_facts: list[dict[str, object]] = []
        for message in messages[:20]:
            if not isinstance(message, dict):
                continue
            fact = {
                "direction": message.get("direction"),
                "message_type": message.get("message_type"),
                "content": message.get("content_masked") or message.get("content"),
            }
            message_facts.append(fact)
            evidence.append(
                {
                    "source_type": "chat_message",
                    "source_id": str(message.get("id", "")),
                    "fact": fact,
                }
            )

        for event in events[:20]:
            if not isinstance(event, dict):
                continue
            occurred_at = event.get("occurred_at")
            fact = {
                "event_type": event.get("event_type"),
                "summary": event.get("summary") or _safe_decrypt(event.get("summary_encrypted")),
                "occurred_at": occurred_at,
            }
            evidence.append(
                {
                    "source_type": "timeline_event",
                    "source_id": str(event.get("id", "")),
                    "fact": fact,
                }
            )

        dimensions = {
            "customer_stage": customer.get("stage"),
            "interested_subject": customer.get("interested_subject"),
            "student_count": len(students),
            "students": student_facts,
            "recent_message_count": len(messages),
            "recent_event_count": len(events),
            "next_action": "由销售顾问结合证据确认下一次沟通重点",
        }
        return {
            "dimensions": dimensions,
            "evidence": evidence,
            "model_name": "mock-rules",
            "model_version": "1",
        }
