from app.ai.state import CustomerAIState


def mock_suggestion_node(state: CustomerAIState) -> dict[str, object]:
    """根据脱敏上下文生成一条本地回复草稿，不调用外部模型。"""

    context = state.get("context", {})
    customer = context.get("customer")
    confirmed_profile = context.get("confirmed_profile")

    if not isinstance(customer, dict) or confirmed_profile is None:
        return {
            "status": "failed",
            "error": "confirmed_profile is required before reply suggestion",
        }

    subject = customer.get("interested_subject") or "当前关注的课程"
    dimensions = (
        confirmed_profile.get("dimensions", {})
        if isinstance(confirmed_profile, dict)
        else {}
    )
    next_action = dimensions.get("next_action") or "进一步了解学习目标"

    suggestion = {
        "suggestion_type": "reply",
        "content": {
            "text": (
                f"您好，结合孩子目前的情况，我们可以先围绕{subject}做一次针对性了解，"
                f"{next_action}，您看哪个时间方便沟通？"
            ),
            "tone": "professional",
            "purpose": "follow_up",
        },
        "evidence_level": "normal",
        "status": "draft",
        "model_name": "mock-rules",
        "model_version": "1",
        "human_confirmation_required": True,
    }

    return {
        "status": "waiting_human",
        "suggestions": [suggestion],
    }
