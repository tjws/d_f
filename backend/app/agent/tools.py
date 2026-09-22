from typing import Any

from sqlalchemy.orm import Session

from app.dao.chat_message_dao import ChatMessageDAO
from app.dao.customer_dao import CustomerDAO
from app.dao.customer_profile_dao import CustomerProfileDAO
from app.dao.timeline_event_dao import TimelineEventDAO


customer_dao = CustomerDAO()
chat_message_dao = ChatMessageDAO()
profile_dao = CustomerProfileDAO()
timeline_event_dao = TimelineEventDAO()


def read_customer_snapshot(db: Session, customer_id: int) -> dict[str, Any]:
    """读取 Agent 规划所需的最小脱敏摘要，不返回密码、密钥或原始敏感正文。"""

    customer = customer_dao.get_by_id(db, customer_id)
    if customer is None:
        raise ValueError("customer not found")

    messages = chat_message_dao.list_by_customer(db, customer_id)
    timeline_events = timeline_event_dao.list_by_customer(db, customer_id)
    profile = profile_dao.get_current_confirmed(db, customer_id)
    # DAO 已按 sent_at 倒序返回。自动决策只看最后一条消息的方向，避免把已经
    # 回复过的历史来信误当成新的待回复事项，进而重复生成相同回复草稿。
    latest_message = messages[0] if messages else None
    latest_message_direction = latest_message.direction if latest_message is not None else None
    latest_inbound = latest_message_direction == "inbound"
    return {
        "customer_id": customer.id,
        "stage": customer.stage,
        "message_count": len(messages),
        "timeline_count": len(timeline_events),
        "has_confirmed_profile": profile is not None,
        "has_inbound_message": latest_inbound,
        "latest_message_direction": latest_message_direction,
        "conversation_state": (
            "needs_sales_reply"
            if latest_message_direction == "inbound"
            else "waiting_customer_reply"
            if latest_message_direction == "outbound"
            else "no_messages"
        ),
    }


def allowed_tool_trace(snapshot: dict[str, Any], selected_tool: str | None = None) -> list[dict[str, str]]:
    """返回可展示的工具调用轨迹；只记录工具名和结果摘要，不记录聊天正文。"""

    trace = [
        {
            "name": "customer.read_context",
            "status": "ok",
            "detail": "读取客户资料、聊天数量和时间线数量（已脱敏）",
        },
        {
            "name": "profile.read_confirmed",
            "status": "ok" if snapshot["has_confirmed_profile"] else "skipped",
            "detail": "已确认画像可用于后续建议"
            if snapshot["has_confirmed_profile"]
            else "暂无已确认画像，回复建议会先停在画像确认点",
        },
        {
            "name": "agent.plan.select_tool",
            "status": "ok" if selected_tool else "skipped",
            "detail": "只从服务端允许的建议生成工具中选择下一步"
            if selected_tool
            else "本次由人工显式选择建议类型，未调用规划器",
        },
        {
            "name": selected_tool or "agent.generate_suggestion",
            "status": "ok",
            "detail": (
                "最近一条为销售已发送消息，等待客户回复，不生成重复草稿"
                if selected_tool == "wait_for_customer_reply"
                else "已交给 LangGraph 生成草稿，尚未执行发送或确认操作"
            ),
        },
        {
            "name": "human_confirmation.require",
            "status": "ok",
            "detail": "Agent 不具备发送权限，必须由人工确认、编辑和发送",
        },
    ]
    return trace
