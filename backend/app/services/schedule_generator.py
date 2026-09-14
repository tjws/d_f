from datetime import datetime, timedelta, timezone
from typing import Any

from app.models.customer import Customer
from app.models.customer_profile import CustomerProfile
from app.models.timeline_event import TimelineEvent


def generate_mock_schedule(customer: Customer, profile: CustomerProfile, events: list[TimelineEvent]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """用确定性规则生成跟进建议，后续可替换为模型但保持输出契约不变。"""
    due_at = customer.next_follow_up_at or datetime.now(timezone.utc) + timedelta(days=1)
    subject = customer.interested_subject or "课程需求"
    content = {
        "title": f"跟进客户：{subject}",
        "description": "结合已确认客户画像，了解最新学习计划并安排下一次沟通。",
        "due_at": due_at.isoformat(),
        "priority": "high" if customer.stage == "following_up" else "normal",
    }
    evidence = [{"source_type": "customer_profile", "source_id": str(profile.id), "fact": "使用已确认客户画像"}]
    evidence.extend({"source_type": "timeline_event", "source_id": str(event.id), "fact": "参考最近跟进记录"} for event in events[:5])
    return content, evidence
