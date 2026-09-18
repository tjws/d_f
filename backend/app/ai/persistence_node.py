from app.ai.state import CustomerAIState
from app.db.session import SessionLocal
from app.services.ai_suggestion_service import persist_graph_reply_draft


def persist_suggestion_node(state: CustomerAIState) -> dict[str, object]:
    """把 Graph 草稿交给业务 Service 持久化，并停在人工确认前。"""

    customer_id = state.get("customer_id")
    actor_user_id = state.get("actor_user_id")
    suggestions = state.get("suggestions", [])

    if not customer_id or not actor_user_id:
        return {
            "status": "failed",
            "error": "customer_id and actor_user_id are required",
        }

    if not suggestions:
        return {
            "status": "failed",
            "error": "suggestion draft is required",
        }

    try:
        with SessionLocal() as db:
            suggestion = persist_graph_reply_draft(
                db,
                customer_id,
                actor_user_id,
                suggestions[0],
            )
    except Exception as exc:
        return {
            "status": "failed",
            "error": str(exc),
        }

    return {
        "status": "waiting_human",
        "suggestion_ids": [suggestion.id],
        "next_action": "review_reply",
    }
