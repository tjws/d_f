from datetime import datetime, timedelta, timezone

from app.ai.providers.base import ScheduleSuggestionPayload


class MockScheduleProvider:
    """本地规则日程 Provider；只生成草稿，不创建正式日程。"""

    def generate(self, context: dict[str, object]) -> ScheduleSuggestionPayload:
        customer = context.get("customer")
        profile = context.get("confirmed_profile")
        events = context.get("timeline_events", [])
        if not isinstance(customer, dict) or not isinstance(profile, dict):
            raise ValueError("customer and confirmed_profile are required")
        if not isinstance(events, list):
            raise ValueError("timeline_events must be a list")

        due_at = self._due_at(customer.get("next_follow_up_at"))
        subject = customer.get("interested_subject") or "课程需求"
        evidence: list[dict[str, object]] = [
            {
                "source_type": "customer_profile",
                "source_id": str(profile.get("id", "")),
                "fact": "使用已确认客户画像",
            }
        ]
        evidence.extend(
            {
                "source_type": "timeline_event",
                "source_id": str(event.get("id", "")),
                "fact": "参考最近跟进记录",
            }
            for event in events[:5]
            if isinstance(event, dict)
        )

        return {
            "content": {
                "title": f"跟进客户：{subject}",
                "description": "结合已确认客户画像，了解最新学习计划并安排下一次沟通。",
                "due_at": due_at.isoformat(),
                "priority": "high" if customer.get("stage") == "following_up" else "normal",
            },
            "evidence": evidence,
            "evidence_level": "sufficient" if len(evidence) > 1 else "normal",
            "model_name": "mock-rules",
            "model_version": "1",
        }

    @staticmethod
    def _due_at(value: object) -> datetime:
        if isinstance(value, str) and value:
            due_at = datetime.fromisoformat(value)
            if due_at.tzinfo is None:
                return due_at.replace(tzinfo=timezone.utc)
            return due_at
        return datetime.now(timezone.utc) + timedelta(days=1)
