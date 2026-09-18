from typing import Any

from app.ai.providers import get_reply_provider
from app.models.chat_message import ChatMessage
from app.models.customer import Customer
from app.models.customer_profile import CustomerProfile
from app.models.timeline_event import TimelineEvent
from app.models.student import Student
from app.knowledge.policy import retrieve_knowledge


def generate_mock_reply(
    customer: Customer,
    profile: CustomerProfile,
    messages: list[ChatMessage],
    events: list[TimelineEvent],
    students: list[Student] | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]], str, str, str]:
    """保留旧服务函数签名，并委托给统一的 MockReplyProvider。"""

    # 旧的 reply-draft API 和 LangGraph 使用同一份 Provider 逻辑，避免输出分叉。
    latest_inbound = next(
        (
            getattr(message, "content_masked", "")
            for message in reversed(messages)
            if getattr(message, "direction", None) == "inbound"
        ),
        "",
    )
    knowledge_result = retrieve_knowledge(latest_inbound, limit=4)
    payload = get_reply_provider().generate(
        {
            "customer": {
                "interested_subject": customer.interested_subject,
            },
            "confirmed_profile": {
                "id": profile.id,
                "dimensions": profile.dimensions_json,
            },
            "messages": [{"id": message.id} for message in messages],
            "timeline_events": [{"id": event.id} for event in events],
            "students": [{"id": student.id} for student in (students or [])],
            "knowledge": [
                {"document_id": item.document_id, "title": item.title, "snippet": item.content[:700], "score": item.score}
                for item in knowledge_result.hits
            ],
            "knowledge_policy": {
                "query": knowledge_result.query,
                "matched": knowledge_result.matched,
                "retrieval_mode": knowledge_result.retrieval_mode,
                "threshold": knowledge_result.threshold,
                "fallback_message": knowledge_result.fallback_message,
            },
        }
    )
    return (
        payload["content"],
        payload["evidence"],
        payload["evidence_level"],
        payload["model_name"],
        payload["model_version"],
    )
