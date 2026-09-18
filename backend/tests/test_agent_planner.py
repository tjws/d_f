from types import SimpleNamespace

import pytest

from app.agent.planner import AgentPlanningError, BailianAgentPlanner


def _planner_with_response(content: str, captured: dict[str, object] | None = None) -> BailianAgentPlanner:
    completion = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
    )
    def create(**kwargs):
        if captured is not None:
            captured.update(kwargs)
        return completion

    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    return BailianAgentPlanner(client=client)


def _snapshot() -> dict[str, object]:
    return {
        "customer_id": 1,
        "stage": "new",
        "message_count": 2,
        "timeline_count": 1,
        "has_confirmed_profile": True,
        "has_inbound_message": True,
    }


def test_bailian_agent_planner_accepts_only_allowed_tool():
    plan = _planner_with_response('{"tool_name":"generate_reply_draft"}').plan(_snapshot(), "请给回复")

    assert plan == {
        "goal": "reply",
        "tool_name": "generate_reply_draft",
        "provider_name": "bailian",
    }


def test_bailian_agent_planner_rejects_send_tool():
    with pytest.raises(AgentPlanningError):
        _planner_with_response('{"tool_name":"send_message"}').plan(_snapshot(), "立即发送")


def test_bailian_agent_planner_sends_only_minimal_snapshot():
    captured: dict[str, object] = {}
    _planner_with_response('{"tool_name":"generate_reply_draft"}', captured).plan(_snapshot(), "请写回复")

    user_prompt = captured["messages"][1]["content"]
    assert "message_count" in user_prompt
    assert "138" not in user_prompt
    assert "聊天正文" not in user_prompt
