from app.ai.providers import get_schedule_provider
from app.ai.state import CustomerAIState


def schedule_suggestion_node(state: CustomerAIState) -> dict[str, object]:
    """根据已确认画像生成日程草稿，不创建正式日程。"""

    context = state.get("context", {})
    if not isinstance(context.get("customer"), dict):
        return {"status": "failed", "error": "customer context is required"}
    if not isinstance(context.get("confirmed_profile"), dict):
        return {
            "status": "failed",
            "error": "confirmed_profile is required before schedule suggestion",
        }

    try:
        payload = get_schedule_provider().generate(context)
    except ValueError as exc:
        return {"status": "failed", "error": str(exc)}

    return {
        "status": "waiting_human",
        "schedule_suggestion": {
            "suggestion_type": "schedule",
            "content": payload["content"],
            "evidence": payload["evidence"],
            "evidence_level": payload["evidence_level"],
            "model_name": payload["model_name"],
            "model_version": payload["model_version"],
        },
    }
