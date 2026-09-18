from typing import Any

from app.ai.providers import get_schedule_provider
from app.models.customer import Customer
from app.models.customer_profile import CustomerProfile
from app.models.timeline_event import TimelineEvent


def generate_mock_schedule(
    customer: Customer,
    profile: CustomerProfile,
    events: list[TimelineEvent],
) -> tuple[dict[str, Any], list[dict[str, Any]], str, str, str]:
    """保留旧函数名，并委托给统一的日程 Provider。"""

    payload = get_schedule_provider().generate(
        {
            "customer": {
                "stage": customer.stage,
                "interested_subject": customer.interested_subject,
                "next_follow_up_at": (
                    customer.next_follow_up_at.isoformat()
                    if customer.next_follow_up_at is not None
                    else None
                ),
            },
            "confirmed_profile": {
                "id": profile.id,
                "dimensions": profile.dimensions_json,
            },
            "timeline_events": [{"id": event.id} for event in events],
        }
    )
    return (
        payload["content"],
        payload["evidence"],
        payload["evidence_level"],
        payload["model_name"],
        payload["model_version"],
    )
