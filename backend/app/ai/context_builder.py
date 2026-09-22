from datetime import datetime

from sqlalchemy.orm import Session

from app.core.crypto import decrypt_text
from app.dao.chat_message_dao import ChatMessageDAO
from app.dao.customer_dao import CustomerDAO
from app.dao.customer_profile_dao import CustomerProfileDAO
from app.dao.student_dao import StudentDAO
from app.dao.timeline_event_dao import TimelineEventDAO
from app.dao.sales_script_dao import SalesScriptDAO
from app.dao.schedule_dao import ScheduleDAO
from app.dao.system_setting_dao import SystemSettingDAO
from app.services.chat_message_service import mask_sensitive_text
from app.models.user import User
from app.knowledge.policy import retrieve_knowledge


customer_dao = CustomerDAO()
profile_dao = CustomerProfileDAO()
chat_message_dao = ChatMessageDAO()
timeline_event_dao = TimelineEventDAO()
student_dao = StudentDAO()
sales_script_dao = SalesScriptDAO()
system_setting_dao = SystemSettingDAO()
schedule_dao = ScheduleDAO()


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def _masked_decrypt(value: str | None) -> str | None:
    """仅在服务端解密，并立即脱敏后放入 AI 上下文。"""

    if value is None:
        return None
    return mask_sensitive_text(decrypt_text(value))


def build_customer_context(
    db: Session,
    customer_id: int,
    actor_user_id: int | None = None,
) -> dict[str, object]:
    """读取并脱敏客户资料，生成供 AI 节点使用的上下文。"""

    customer = customer_dao.get_by_id(db, customer_id)
    if customer is None:
        raise ValueError(f"customer {customer_id} not found")

    confirmed_profile = profile_dao.get_current_confirmed(db, customer_id)
    students = student_dao.list_by_customer(db, customer_id)
    messages = chat_message_dao.list_by_customer(db, customer_id)
    timeline_events = timeline_event_dao.list_by_customer(db, customer_id)
    completed_follow_ups = schedule_dao.list_completed_by_customer(db, customer_id)
    # 消息 DAO 按发送时间倒序返回。只有会话最后一条确实来自客户时，才把它
    # 作为本次回复/RAG 的问题；不能回头拿历史来信生成重复回复。
    latest_message = messages[0] if messages else None
    latest_inbound = (
        latest_message.content_masked
        if latest_message is not None and latest_message.direction == "inbound"
        else ""
    )
    # 运营人员可以调整召回条数，但异常值会在 DAO 中回退为安全默认值。
    knowledge_limit = system_setting_dao.get_global_int(db, "knowledge_max_results", 4)
    actor = db.get(User, actor_user_id) if actor_user_id is not None else None
    consultant_name = (actor.full_name or actor.username) if actor is not None else None
    knowledge_result = retrieve_knowledge(
        latest_inbound,
        limit=knowledge_limit,
        db=db,
        consultant_name=consultant_name,
    )
    published_scripts = sales_script_dao.search_published(db, latest_inbound, limit=knowledge_limit) if latest_inbound else []

    return {
        "customer": {
            "id": customer.id,
            "name": customer.name,
            # 手机号只保留脱敏版本，禁止把原始号码送入 AI 上下文。
            "phone": mask_sensitive_text(customer.phone),
            "student_name": customer.student_name,
            "grade": customer.grade,
            "interested_subject": customer.interested_subject,
            "stage": customer.stage,
            "source": customer.source,
            "remark": mask_sensitive_text(customer.remark or ""),
            "next_follow_up_at": _iso(customer.next_follow_up_at),
        },
        # 只有人工确认过的画像才能作为后续建议的可信上下文。
        "confirmed_profile": (
            {
                "id": confirmed_profile.id,
                "version": confirmed_profile.version,
                "dimensions": confirmed_profile.dimensions_json,
                "evidence": confirmed_profile.evidence_json,
            }
            if confirmed_profile is not None
            else None
        ),
        # 学生资料是生成画像的依据；仅保留脱敏字段，不能把加密原文交给 Provider。
        "students": [
            {
                "id": student.id,
                "grade": student.grade,
                "gender": student.gender,
                "school": _masked_decrypt(student.school_encrypted),
                "subjects": student.subjects_json or {},
            }
            for student in students
        ],
        "messages": [
            {
                "id": message.id,
                "direction": message.direction,
                "message_type": message.message_type,
                "content": message.content_masked,
                "sent_at": _iso(message.sent_at),
            }
            for message in messages[:20]
        ],
        "timeline_events": [
            {
                "id": event.id,
                "event_type": event.event_type,
                "summary": mask_sensitive_text(decrypt_text(event.summary_encrypted)),
                "source": event.source,
                "occurred_at": _iso(event.occurred_at),
            }
            for event in timeline_events[:20]
        ],
        # 日程结果是内部人员主动回填的事实，单独提供给模型，不能仅靠解析时间线文案猜测。
        # 备注可能包含个人信息，送入 Provider 前同样进行脱敏。
        "completed_follow_ups": [
            {
                "id": schedule.id,
                "title": schedule.title,
                "outcome": schedule.outcome or "other",
                "completion_note": mask_sensitive_text(schedule.completion_note or ""),
                "completed_at": _iso(schedule.completed_at),
            }
            for schedule in completed_follow_ups
        ],
        # RAG 资料来自仓库内固定文档，不把客户隐私写回知识库。
        "knowledge": [
            {"document_id": item.document_id, "chunk_id": item.chunk_id, "title": item.title, "snippet": item.content[:700], "score": item.score}
            for item in knowledge_result.hits
        ],
        # 把检索策略结果显式传给 Provider，避免模型把低质量候选当成事实。
        "knowledge_policy": {
            "query": knowledge_result.query,
            "matched": knowledge_result.matched,
            "retrieval_mode": knowledge_result.retrieval_mode,
            "threshold": knowledge_result.threshold,
            "fallback_message": knowledge_result.fallback_message,
        },
        # 只有审核发布的话术才允许进入 AI 上下文；草稿不会影响模型输出。
        "sales_scripts": [
            {"id": script.id, "title": script.title, "scene": script.scene, "content": script.content, "tone": script.tone, "version": script.version}
            for script in published_scripts
        ],
    }
