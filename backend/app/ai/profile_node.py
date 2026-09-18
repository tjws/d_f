from app.ai.providers import get_profile_provider
from app.ai.state import CustomerAIState


def profile_draft_node(state: CustomerAIState) -> dict[str, object]:
    """生成客户画像草稿；草稿尚未确认，不能作为回复建议的依据。"""

    context = state.get("context", {})
    if not isinstance(context.get("customer"), dict):
        return {
            "status": "failed",
            "error": "customer context is required",
        }

    try:
        payload = get_profile_provider().generate(context)
    except ValueError as exc:
        return {
            "status": "failed",
            "error": str(exc),
        }

    return {
        "status": "waiting_human",
        "profile_draft": dict(payload),
    }
