from app.ai.providers import get_tag_provider
from app.ai.state import CustomerAIState


def tag_suggestion_node(state: CustomerAIState) -> dict[str, object]:
    """根据已确认画像生成标签候选项，不直接把标签设为已生效。"""

    context = state.get("context", {})
    if not isinstance(context.get("customer"), dict):
        return {"status": "failed", "error": "customer context is required"}
    if not isinstance(context.get("confirmed_profile"), dict):
        return {
            "status": "failed",
            "error": "confirmed_profile is required before tag suggestion",
        }

    try:
        payload = get_tag_provider().generate(context)
    except ValueError as exc:
        return {"status": "failed", "error": str(exc)}

    return {
        "status": "waiting_human",
        "tag_payload": dict(payload),
    }
