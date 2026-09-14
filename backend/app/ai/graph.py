from langgraph.graph import END, START, StateGraph

from app.ai.state import CustomerAIState
from app.ai.context_builder import build_customer_context
from app.ai.persistence_node import persist_suggestion_node
from app.ai.suggestion_node import mock_suggestion_node
from app.db.session import SessionLocal


def prepare_context(state: CustomerAIState) -> dict[str, object]:
    """读取客户上下文并推进状态；失败时返回可观察的工作流错误。"""

    customer_id = state.get("customer_id")
    if not customer_id:
        return {
            "status": "failed",
            "error": "customer_id is required",
        }

    try:
        with SessionLocal() as db:
            context = build_customer_context(db, customer_id)
    except ValueError as exc:
        return {
            "status": "failed",
            "error": str(exc),
        }

    return {
        "status": "context_ready",
        "context": context,
    }


def build_customer_ai_graph():
    """构建客户 AI 工作流；后续再逐步增加画像、建议和人工确认节点。"""

    builder = StateGraph(CustomerAIState)
    builder.add_node("prepare_context", prepare_context)
    builder.add_node("mock_suggestion", mock_suggestion_node)
    builder.add_node("persist_suggestion", persist_suggestion_node)
    builder.add_edge(START, "prepare_context")
    builder.add_edge("prepare_context", "mock_suggestion")
    builder.add_edge("mock_suggestion", "persist_suggestion")
    builder.add_edge("persist_suggestion", END)
    return builder.compile()


customer_ai_graph = build_customer_ai_graph()
