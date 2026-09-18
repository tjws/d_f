from app.ai.state import CustomerAIState
from app.db.session import SessionLocal
from app.services.customer_profile_service import persist_graph_profile_draft


def persist_profile_draft_node(state: CustomerAIState) -> dict[str, object]:
    """保存画像草稿和审计日志，并停在必须人工确认的边界。"""

    customer_id = state.get("customer_id")
    actor_user_id = state.get("actor_user_id")
    profile_draft = state.get("profile_draft")

    if not customer_id or not actor_user_id:
        return {
            "status": "failed",
            "error": "customer_id and actor_user_id are required",
        }
    if not isinstance(profile_draft, dict):
        return {
            "status": "failed",
            "error": "profile draft is required",
        }

    try:
        with SessionLocal() as db:
            profile = persist_graph_profile_draft(
                db,
                customer_id,
                actor_user_id,
                profile_draft,
            )
    except Exception as exc:
        return {
            "status": "failed",
            "error": str(exc),
        }

    return {
        "status": "waiting_human",
        "profile_id": profile.id,
        "next_action": "confirm_profile",
    }
