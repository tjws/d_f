from typing import Any

from app.models.chat_message import ChatMessage
from app.models.customer import Customer
from app.models.customer_profile import CustomerProfile
from app.models.timeline_event import TimelineEvent


def generate_mock_reply(customer: Customer, profile: CustomerProfile, messages: list[ChatMessage], events: list[TimelineEvent]) -> tuple[dict[str, Any], list[dict[str, Any]], str]:
    """生成可预测的回复草稿，后续真实模型只需替换这个生成器。"""
    dimensions = profile.dimensions_json
    subject = customer.interested_subject or "目前关注的课程"
    next_action = dimensions.get("next_action") or "进一步了解孩子的学习目标"
    text = f"您好，结合孩子目前的情况，我们可以先围绕{subject}做一次针对性了解。{next_action}，您看哪个时间方便沟通？"
    evidence = [{"source_type": "customer_profile", "source_id": str(profile.id), "fact": "使用已确认客户画像"}]
    evidence.extend({"source_type": "chat_message", "source_id": str(message.id), "fact": "使用最近聊天消息"} for message in messages[:5])
    evidence.extend({"source_type": "timeline_event", "source_id": str(event.id), "fact": "使用最近跟进事件"} for event in events[:5])
    level = "sufficient" if messages or events else "normal"
    return {"text": text, "tone": "professional", "purpose": "follow_up"}, evidence, level
