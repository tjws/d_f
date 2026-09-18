from langgraph.graph import END, START, StateGraph

from app.ai.state import CustomerAIState
from app.ai.context_builder import build_customer_context
from app.ai.persistence_node import persist_suggestion_node
from app.ai.profile_node import profile_draft_node
from app.ai.profile_persistence_node import persist_profile_draft_node
from app.ai.schedule_persistence_node import persist_schedule_suggestion_node
from app.ai.schedule_suggestion_node import schedule_suggestion_node
from app.ai.suggestion_node import mock_suggestion_node
from app.ai.tag_persistence_node import persist_tag_suggestions_node
from app.ai.tag_suggestion_node import tag_suggestion_node
from app.db.session import SessionLocal


def prepare_context(state: CustomerAIState) -> dict[str, object]:
    """读取客户上下文并推进状态；失败时返回可观察的工作流错误。"""

    customer_id = state.get("customer_id")
    if not customer_id:
        return {
            "status": "failed",
            "error": "customer_id is required",
        }

    if state.get("workflow_goal", "reply") not in {"profile", "reply", "tag", "schedule"}:
        return {
            "status": "failed",
            "error": "workflow_goal must be profile, reply, tag, or schedule",
        }

    try:
        with SessionLocal() as db:
            context = build_customer_context(db, customer_id, state.get("actor_user_id"))
    except ValueError as exc:
        return {
            "status": "failed",
            "error": str(exc),
        }

    return {
        "status": "context_ready",
        "context": context,
    }


def route_after_context(state: CustomerAIState) -> str:
    """确认画像前只走画像草稿分支，防止未经人工确认直接生成回复。"""

    if state.get("status") == "failed":
        return "end"

    context = state.get("context", {})
    goal = state.get("workflow_goal", "reply")

    # profile 是显式入口：即使已有确认画像，也允许人工要求生成新版本草稿。
    if goal == "profile":
        return "profile"

    if not isinstance(context.get("confirmed_profile"), dict):
        return "profile"

    if goal == "tag":
        return "tag"
    if goal == "schedule":
        return "schedule"
    if goal == "reply":
        return "reply"
    return "end"


def build_customer_ai_graph():
    """构建画像优先的工作流，所有分支均在人工确认点结束。"""

    builder = StateGraph(CustomerAIState)
    builder.add_node("prepare_context", prepare_context)
    builder.add_node("profile_draft", profile_draft_node)
    builder.add_node("persist_profile_draft", persist_profile_draft_node)
    builder.add_node("mock_suggestion", mock_suggestion_node)
    builder.add_node("persist_suggestion", persist_suggestion_node)
    builder.add_node("tag_suggestion", tag_suggestion_node)
    builder.add_node("persist_tag_suggestions", persist_tag_suggestions_node)
    builder.add_node("schedule_suggestion", schedule_suggestion_node)
    builder.add_node("persist_schedule_suggestion", persist_schedule_suggestion_node)
    builder.add_edge(START, "prepare_context")
    builder.add_conditional_edges(
        "prepare_context",
        route_after_context,
        {
            "profile": "profile_draft",
            "reply": "mock_suggestion",
            "tag": "tag_suggestion",
            "schedule": "schedule_suggestion",
            "end": END,
        },
    )
    builder.add_edge("profile_draft", "persist_profile_draft")
    builder.add_edge("persist_profile_draft", END)
    builder.add_edge("mock_suggestion", "persist_suggestion")
    builder.add_edge("persist_suggestion", END)
    builder.add_edge("tag_suggestion", "persist_tag_suggestions")
    builder.add_edge("persist_tag_suggestions", END)
    builder.add_edge("schedule_suggestion", "persist_schedule_suggestion")
    builder.add_edge("persist_schedule_suggestion", END)
    return builder.compile()


customer_ai_graph = build_customer_ai_graph()
