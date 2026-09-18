from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.ai.providers import (
    MockProfileProvider,
    MockReplyProvider,
    MockScheduleProvider,
    MockTagProvider,
    get_profile_provider,
    get_reply_provider,
    get_schedule_provider,
    get_tag_provider,
)
from app.services.profile_generator import generate_mock_profile
from app.services.reply_generator import generate_mock_reply
from app.services.schedule_generator import generate_mock_schedule


def test_mock_reply_provider_returns_versioned_draft_payload():
    payload = MockReplyProvider().generate(
        {
            "customer": {
                "interested_subject": "数学",
            },
            "confirmed_profile": {
                "id": 7,
                "dimensions": {
                    "next_action": "确认试听时间",
                },
            },
            "messages": [{"id": 11}],
            "timeline_events": [],
        }
    )

    assert payload["model_name"] == "mock-rules"
    assert payload["model_version"] == "1"
    assert payload["evidence_level"] == "sufficient"
    assert "数学" in str(payload["content"])
    assert payload["evidence"][0]["source_type"] == "customer_profile"


def test_mock_reply_provider_requires_confirmed_profile():
    try:
        MockReplyProvider().generate({"customer": {}})
    except ValueError as exc:
        assert "confirmed_profile" in str(exc)
    else:
        raise AssertionError("expected a confirmed profile validation error")


def test_mock_reply_provider_cites_human_completed_follow_up():
    payload = MockReplyProvider().generate(
        {
            "customer": {"interested_subject": "英语"},
            "confirmed_profile": {"id": 7, "dimensions": {"next_action": "确认试听安排"}},
            "completed_follow_ups": [{"id": 31, "outcome": "appointment"}],
        }
    )

    assert "appointment" in str(payload["content"])
    assert any(item["source_type"] == "schedule_completion" and item["source_id"] == "31" for item in payload["evidence"])


def test_provider_factories_default_to_mock(monkeypatch):
    monkeypatch.delenv("AI_REPLY_PROVIDER", raising=False)
    monkeypatch.delenv("AI_PROFILE_PROVIDER", raising=False)
    monkeypatch.delenv("AI_TAG_PROVIDER", raising=False)
    monkeypatch.delenv("AI_SCHEDULE_PROVIDER", raising=False)

    assert isinstance(get_reply_provider(), MockReplyProvider)
    assert isinstance(get_profile_provider(), MockProfileProvider)
    assert isinstance(get_tag_provider(), MockTagProvider)
    assert isinstance(get_schedule_provider(), MockScheduleProvider)


@pytest.mark.parametrize(
    ("setting_name", "factory"),
    [
        ("AI_REPLY_PROVIDER", get_reply_provider),
        ("AI_PROFILE_PROVIDER", get_profile_provider),
        ("AI_TAG_PROVIDER", get_tag_provider),
        ("AI_SCHEDULE_PROVIDER", get_schedule_provider),
    ],
)
def test_provider_factory_rejects_unknown_provider(monkeypatch, setting_name, factory):
    monkeypatch.setenv(setting_name, "unknown")

    with pytest.raises(ValueError, match=setting_name):
        factory()


def test_legacy_reply_generator_delegates_to_the_same_provider():
    customer = SimpleNamespace(interested_subject="英语")
    profile = SimpleNamespace(id=8, dimensions_json={"next_action": "安排试听"})
    messages = [SimpleNamespace(id=12)]
    events = [SimpleNamespace(id=13)]

    content, evidence, level, model_name, model_version = generate_mock_reply(
        customer,
        profile,
        messages,
        events,
    )
    payload = MockReplyProvider().generate(
        {
            "customer": {"interested_subject": "英语"},
            "confirmed_profile": {"id": 8, "dimensions": {"next_action": "安排试听"}},
            "messages": [{"id": 12}],
            "timeline_events": [{"id": 13}],
        }
    )

    assert content == payload["content"]
    assert evidence == payload["evidence"]
    assert level == payload["evidence_level"]
    assert (model_name, model_version) == (
        payload["model_name"],
        payload["model_version"],
    )


def test_mock_profile_provider_returns_dimensions_and_evidence():
    payload = MockProfileProvider().generate(
        {
            "customer": {"stage": "following_up", "interested_subject": "数学"},
            "students": [
                {
                    "id": 3,
                    "grade": "小学五年级",
                    "gender": None,
                    "school_encrypted": None,
                    "subjects": {"math": True},
                }
            ],
            "messages": [{"id": 4, "direction": "inbound", "message_type": "text", "content_masked": "想了解课程"}],
            "timeline_events": [],
        }
    )

    assert payload["dimensions"]["student_count"] == 1
    assert payload["dimensions"]["interested_subject"] == "数学"
    assert {item["source_type"] for item in payload["evidence"]} == {"student", "chat_message"}


def test_legacy_profile_generator_delegates_to_the_same_provider():
    customer = SimpleNamespace(stage="following_up", interested_subject="英语")
    students = [
        SimpleNamespace(
            id=15,
            grade="小学六年级",
            gender=None,
            school_encrypted=None,
            subjects_json={"english": True},
        )
    ]
    messages = [
        SimpleNamespace(
            id=16,
            direction="inbound",
            message_type="text",
            content_masked="想试听",
        )
    ]
    events = []

    dimensions, evidence, model_name, model_version = generate_mock_profile(
        customer,
        students,
        messages,
        events,
    )
    payload = MockProfileProvider().generate(
        {
            "customer": {"stage": "following_up", "interested_subject": "英语"},
            "students": [
                {
                    "id": 15,
                    "grade": "小学六年级",
                    "gender": None,
                    "school_encrypted": None,
                    "subjects": {"english": True},
                }
            ],
            "messages": [
                {
                    "id": 16,
                    "direction": "inbound",
                    "message_type": "text",
                    "content_masked": "想试听",
                }
            ],
            "timeline_events": [],
        }
    )

    assert dimensions == payload["dimensions"]
    assert evidence == payload["evidence"]
    assert (model_name, model_version) == (
        payload["model_name"],
        payload["model_version"],
    )


def test_mock_tag_provider_generates_confirmable_candidates():
    payload = MockTagProvider().generate(
        {
            "customer": {
                "id": 21,
                "interested_subject": "数学",
                "stage": "following_up",
            },
            "confirmed_profile": {
                "id": 22,
                "dimensions": {"student_count": 1},
            },
        }
    )

    assert payload["model_name"] == "mock-rules"
    assert {item["key"] for item in payload["candidates"]} == {
        "subject_math",
        "follow_up_active",
        "has_student_profile",
    }
    assert all(item["evidence"] for item in payload["candidates"])


def test_mock_schedule_provider_and_legacy_wrapper_match():
    due_at = datetime(2026, 9, 18, 9, 0, tzinfo=timezone.utc)
    customer = SimpleNamespace(
        stage="following_up",
        interested_subject="英语",
        next_follow_up_at=due_at,
    )
    profile = SimpleNamespace(id=31, dimensions_json={})
    events = [SimpleNamespace(id=32)]

    content, evidence, evidence_level, model_name, model_version = generate_mock_schedule(
        customer,
        profile,
        events,
    )
    payload = MockScheduleProvider().generate(
        {
            "customer": {
                "stage": "following_up",
                "interested_subject": "英语",
                "next_follow_up_at": due_at.isoformat(),
            },
            "confirmed_profile": {"id": 31, "dimensions": {}},
            "timeline_events": [{"id": 32}],
        }
    )

    assert content == payload["content"]
    assert evidence == payload["evidence"]
    assert evidence_level == payload["evidence_level"]
    assert (model_name, model_version) == (
        payload["model_name"],
        payload["model_version"],
    )
