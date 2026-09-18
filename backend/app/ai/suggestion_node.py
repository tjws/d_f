from app.ai.state import CustomerAIState
from app.ai.providers import get_reply_provider


def mock_suggestion_node(state: CustomerAIState) -> dict[str, object]:
    """调用当前 Provider 生成回复草稿，并标记为等待人工确认。"""

    context = state.get("context", {})
    customer = context.get("customer")
    confirmed_profile = context.get("confirmed_profile")

    if not isinstance(customer, dict) or confirmed_profile is None:
        return {
            "status": "failed",
            "error": "confirmed_profile is required before reply suggestion",
        }

    try:
        payload = get_reply_provider().generate(context)
    except ValueError as exc:
        return {
            "status": "failed",
            "error": str(exc),
        }

    suggestion = {
        "suggestion_type": "reply",
        "content": payload["content"],
        "evidence": payload["evidence"],
        "evidence_level": payload["evidence_level"],
        "status": "draft",
        "model_name": payload["model_name"],
        "model_version": payload["model_version"],
        "human_confirmation_required": True,
    }

    return {
        "status": "waiting_human",
        "suggestions": [suggestion],
    }
