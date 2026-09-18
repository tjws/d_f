from app.ai.state import CustomerAIState
from app.db.session import SessionLocal
from app.services.schedule_service import persist_graph_schedule_suggestion


def persist_schedule_suggestion_node(state: CustomerAIState) -> dict[str, object]:
    """保存待确认日程建议和审计日志，正式日程仍由人工确认后创建。"""

    customer_id = state.get("customer_id")
    actor_user_id = state.get("actor_user_id")
    schedule_suggestion = state.get("schedule_suggestion")
    if not customer_id or not actor_user_id:
        return {
            "status": "failed",
            "error": "customer_id and actor_user_id are required",
        }
    if not isinstance(schedule_suggestion, dict):
        return {"status": "failed", "error": "schedule suggestion is required"}

    try:
        with SessionLocal() as db:
            suggestion = persist_graph_schedule_suggestion(
                db,
                customer_id,
                actor_user_id,
                schedule_suggestion,
            )
    except Exception as exc:
        return {"status": "failed", "error": str(exc)}

    return {
        "status": "waiting_human",
        "suggestion_ids": [suggestion.id],
        "next_action": "review_schedule",
    }
