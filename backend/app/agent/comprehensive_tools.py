"""第二层 Agent 的五个只读工具。

每个工具只查询一个数据域并返回脱敏摘要；写入建议、人工确认和发送仍由既有 Service 负责。
"""

from dataclasses import dataclass
from datetime import datetime
from time import perf_counter
from typing import Any, Literal

from sqlalchemy.orm import Session

from app.agent.catalog import list_course_openings
from app.dao.chat_message_dao import ChatMessageDAO
from app.dao.course_order_dao import CourseOrderDAO
from app.dao.customer_profile_dao import CustomerProfileDAO
from app.dao.customer_tag_dao import CustomerTagDAO
from app.dao.customer_dao import CustomerDAO
from app.knowledge.policy import retrieve_knowledge
from app.services.ai_rag_telemetry_service import record_rag_interaction


ToolStatus = Literal["ok", "incomplete", "error", "skipped"]


@dataclass(frozen=True)
class ComprehensiveToolResult:
    name: str
    status: ToolStatus
    summary: str
    data: dict[str, Any]
    evidence: list[dict[str, Any]]
    missing_inputs: list[str]

    def as_step(self, step_number: int) -> dict[str, Any]:
        """转换为可存入 workflow result_json、也可供侧边栏展示的步骤记录。"""

        return {
            "step": step_number,
            "tool_name": self.name,
            "status": self.status,
            "summary": self.summary,
            "data": self.data,
            "evidence": self.evidence,
            "missing_inputs": self.missing_inputs,
        }


customer_dao = CustomerDAO()
chat_message_dao = ChatMessageDAO()
profile_dao = CustomerProfileDAO()
order_dao = CourseOrderDAO()
customer_tag_dao = CustomerTagDAO()


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def _knowledge_step(
    db: Session,
    customer_id: int,
    consultant_name: str | None,
    run_id: int | None = None,
    actor_user_id: int | None = None,
) -> ComprehensiveToolResult:
    messages = chat_message_dao.list_by_customer(db, customer_id)
    latest_inbound = next((message.content_masked for message in messages if message.direction == "inbound"), "")
    started = perf_counter()
    result = retrieve_knowledge(
        latest_inbound,
        limit=4,
        db=db,
        consultant_name=consultant_name,
    )
    record_rag_interaction(
        db,
        customer_id=customer_id,
        actor_user_id=actor_user_id,
        run_id=run_id,
        suggestion_id=None,
        entrypoint="comprehensive_agent",
        query=result.query,
        retrieval_mode=result.retrieval_mode,
        matched=result.matched,
        fallback=bool(result.query) and not result.matched,
        duration_ms=round((perf_counter() - started) * 1000),
        metadata={
            "hit_count": len(result.hits),
            "document_ids": [item.document_id for item in result.hits[:10]],
        },
    )
    data = {
        "query": result.query,
        "matched": result.matched,
        "retrieval_mode": result.retrieval_mode,
        "threshold": result.threshold,
        "titles": [item.title for item in result.hits[:5]],
    }
    evidence = [
        {
            "source_type": "knowledge",
            "source_id": f"{item.document_id}:{item.chunk_id or ''}",
            "fact": item.title,
            "snippet": item.content[:240],
        }
        for item in result.hits[:5]
    ]
    if not result.query:
        return ComprehensiveToolResult(
            "knowledge.search",
            "incomplete",
            "没有最新的家长入站问题，无法进行事实资料匹配。",
            data,
            evidence,
            ["latest_inbound_message"],
        )
    if not result.matched:
        data["fallback_message"] = result.fallback_message
        return ComprehensiveToolResult(
            "knowledge.search",
            "incomplete",
            "未找到达到证据阈值的官方资料，需要顾问人工核实。",
            data,
            evidence,
            ["verified_knowledge_match"],
        )
    return ComprehensiveToolResult(
        "knowledge.search",
        "ok",
        f"找到 {len(result.hits)} 条达到阈值的官方资料。",
        data,
        evidence,
        [],
    )


def _profile_step(db: Session, customer_id: int) -> ComprehensiveToolResult:
    profile = profile_dao.get_current_confirmed(db, customer_id)
    if profile is None:
        return ComprehensiveToolResult(
            "customer_profile.read_confirmed",
            "incomplete",
            "当前没有人工确认的客户画像，不能把画像结论当成事实。",
            {"profile_id": None},
            [],
            ["confirmed_profile"],
        )
    dimensions = profile.dimensions_json if isinstance(profile.dimensions_json, dict) else {}
    return ComprehensiveToolResult(
        "customer_profile.read_confirmed",
        "ok",
        f"读取到已确认画像 v{profile.version}。",
        {"profile_id": profile.id, "version": profile.version, "dimension_keys": list(dimensions)[:20]},
        [{"source_type": "customer_profile", "source_id": str(profile.id), "fact": f"confirmed:v{profile.version}"}],
        [],
    )


def _orders_step(db: Session, customer_id: int) -> ComprehensiveToolResult:
    orders = order_dao.list_by_customer(db, customer_id)
    items = [
        {
            "id": order.id,
            "course_name": order.course_name,
            "status": order.status,
            "amount": str(order.amount),
            "ordered_at": _iso(order.ordered_at),
        }
        for order in orders[:10]
    ]
    return ComprehensiveToolResult(
        "orders.list",
        "ok" if items else "incomplete",
        f"读取到 {len(items)} 条课程订单记录。" if items else "当前客户没有课程订单记录。",
        {"count": len(items), "items": items},
        [{"source_type": "course_order", "source_id": str(item["id"]), "fact": item["status"]} for item in items],
        [] if items else ["course_orders"],
    )


def _tags_step(db: Session, customer_id: int) -> ComprehensiveToolResult:
    customer_tags = customer_tag_dao.list_by_customer(db, customer_id)
    items = [
        {
            "id": item.id,
            "key": item.tag.key if item.tag is not None else None,
            "name": item.tag.name if item.tag is not None else None,
            "category": item.tag.category if item.tag is not None else None,
            "status": item.status,
        }
        for item in customer_tags[:20]
    ]
    return ComprehensiveToolResult(
        "tags.analyze",
        "ok" if items else "incomplete",
        f"读取到 {len(items)} 个客户标签。" if items else "当前客户没有已保存标签。",
        {"count": len(items), "items": items},
        [{"source_type": "customer_tag", "source_id": str(item["id"]), "fact": item["status"]} for item in items],
        [] if items else ["customer_tags"],
    )


def _course_openings_step(db: Session, customer_id: int) -> ComprehensiveToolResult:
    customer = customer_dao.get_by_id(db, customer_id)
    if customer is None:
        return ComprehensiveToolResult(
            "course_openings.read",
            "error",
            "客户不存在，无法筛选课程资料。",
            {},
            [],
            ["customer"],
        )
    items = list_course_openings(customer.interested_subject, customer.grade)
    return ComprehensiveToolResult(
        "course_openings.read",
        "ok",
        f"匹配到 {len(items)} 条本地课程/开班资料；座位和实时库存仍需人工核实。",
        {"source": "local_demo_catalog", "items": items},
        [{"source_type": "course_catalog", "source_id": item["course_name"], "fact": "static_demo_data"} for item in items],
        ["realtime_seat_availability"],
    )


def execute_comprehensive_tool(
    db: Session,
    customer_id: int,
    tool_name: str,
    consultant_name: str | None = None,
    run_id: int | None = None,
    actor_user_id: int | None = None,
) -> ComprehensiveToolResult:
    """执行单个白名单工具；未知工具不会被静默执行。"""

    if tool_name == "knowledge.search":
        return _knowledge_step(db, customer_id, consultant_name, run_id, actor_user_id)
    if tool_name == "customer_profile.read_confirmed":
        return _profile_step(db, customer_id)
    if tool_name == "orders.list":
        return _orders_step(db, customer_id)
    if tool_name == "tags.analyze":
        return _tags_step(db, customer_id)
    if tool_name == "course_openings.read":
        return _course_openings_step(db, customer_id)
    raise ValueError(f"unsupported comprehensive agent tool: {tool_name}")


__all__ = ["ComprehensiveToolResult", "ToolStatus", "execute_comprehensive_tool"]
