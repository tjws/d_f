from app.ai.state import CustomerAIState
from app.db.session import SessionLocal
from app.services.tag_service import persist_graph_tag_suggestions


def persist_tag_suggestions_node(state: CustomerAIState) -> dict[str, object]:
    """写入待确认标签及审计日志，不能自动确认标签。"""

    customer_id = state.get("customer_id")
    actor_user_id = state.get("actor_user_id")
    tag_payload = state.get("tag_payload")
    if not customer_id or not actor_user_id:
        return {
            "status": "failed",
            "error": "customer_id and actor_user_id are required",
        }
    if not isinstance(tag_payload, dict):
        return {"status": "failed", "error": "tag payload is required"}

    try:
        with SessionLocal() as db:
            customer_tags = persist_graph_tag_suggestions(
                db,
                customer_id,
                actor_user_id,
                tag_payload,
            )
    except Exception as exc:
        return {"status": "failed", "error": str(exc)}

    return {
        "status": "waiting_human",
        "customer_tag_ids": [item.id for item in customer_tags],
        "next_action": "confirm_tags",
    }
