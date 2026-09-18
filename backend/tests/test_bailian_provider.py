import json
from types import SimpleNamespace

import pytest

from app.ai.providers.bailian import (
    BailianProfileProvider,
    BailianProviderError,
    BailianReplyProvider,
    BailianScheduleProvider,
    BailianTagProvider,
)
from app.ai.providers.factory import get_reply_provider
from app.ai.providers.factory import get_schedule_provider


class FakeBailianClient:
    """模拟 OpenAI 兼容 SDK，测试不发起真实网络请求。"""

    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload
        self.calls: list[dict[str, object]] = []
        self.chat = SimpleNamespace(completions=self)

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(self.payload)))],
            model="qwen-plus-test",
        )


def _context() -> dict[str, object]:
    return {
        "customer": {"id": 1, "interested_subject": "英语", "stage": "following_up"},
        "confirmed_profile": {"id": 2, "dimensions": {"next_action": "安排试听"}},
        "students": [{"id": 3, "grade": "初一"}],
        "messages": [{"id": 4, "content": "已脱敏消息"}],
        "timeline_events": [{"id": 5, "summary": "已脱敏时间线"}],
    }


def test_bailian_reply_provider_uses_json_mode_and_local_evidence():
    client = FakeBailianClient(
        {"content": {"text": "您好，方便安排英语试听吗？", "tone": "friendly", "purpose": "follow_up"}}
    )
    payload = BailianReplyProvider(client=client).generate(_context())

    assert payload["content"]["text"] == "您好，方便安排英语试听吗？"
    assert payload["model_name"] == "bailian:qwen-plus"
    assert {item["source_type"] for item in payload["evidence"]} == {
        "customer_profile",
        "chat_message",
        "timeline_event",
    }
    assert client.calls[0]["response_format"] == {"type": "json_object"}
    assert "JSON" in client.calls[0]["messages"][0]["content"]


@pytest.mark.parametrize(
    ("provider", "response", "expected_key"),
    [
        (BailianProfileProvider, {"dimensions": {"next_action": "确认试听"}}, "dimensions"),
        (BailianTagProvider, {"candidates": [{"key": "english_interest", "name": "英语兴趣", "category": "学习兴趣", "description": "关注英语课程", "color": "#3B82F6"}]}, "candidates"),
        (BailianScheduleProvider, {"content": {"title": "英语回访", "description": "确认试听", "due_at": "2026-09-16T09:00:00+00:00", "priority": "high"}}, "content"),
    ],
)
def test_bailian_providers_validate_structured_fake_response(provider, response, expected_key):
    payload = provider(client=FakeBailianClient(response)).generate(_context())
    assert payload[expected_key]
    assert payload["model_version"] == "qwen-plus-test"


def test_bailian_provider_requires_api_key_when_creating_real_client(monkeypatch):
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)
    with pytest.raises(BailianProviderError, match="DASHSCOPE_API_KEY"):
        BailianReplyProvider().generate(_context())


def test_provider_factory_can_select_bailian(monkeypatch):
    monkeypatch.setenv("AI_REPLY_PROVIDER", "bailian")
    assert isinstance(get_reply_provider(), BailianReplyProvider)


def test_global_provider_setting_applies_when_module_setting_is_missing(monkeypatch):
    monkeypatch.delenv("AI_SCHEDULE_PROVIDER", raising=False)
    monkeypatch.setenv("AI_PROVIDER", "bailian")
    assert isinstance(get_schedule_provider(), BailianScheduleProvider)
