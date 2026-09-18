from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.crypto import encrypt_text
from app.dao.ai_suggestion_dao import AISuggestionDAO
from app.dao.customer_profile_dao import CustomerProfileDAO
from app.dao.schedule_dao import ScheduleDAO
from app.dao.timeline_event_dao import TimelineEventDAO
from app.models.ai_suggestion import AISuggestion
from app.models.schedule import Schedule
from app.models.timeline_event import TimelineEvent
from app.models.user import User
from app.schemas.ai_suggestion import AISuggestionStatus, AISuggestionUpdate
from app.schemas.schedule import ScheduleCompletion, ScheduleUpdate
from app.services.audit_log_service import append_audit_log
from app.services.customer_service import get_customer_or_404
from app.services.ai_suggestion_feedback_service import record_feedback


suggestion_dao = AISuggestionDAO()
profile_dao = CustomerProfileDAO()
schedule_dao = ScheduleDAO()
timeline_event_dao = TimelineEventDAO()


def _get_schedule_suggestion_or_404(db: Session, customer_id: int, suggestion_id: int) -> AISuggestion:
    suggestion = suggestion_dao.get_by_id(db, customer_id, suggestion_id)
    if suggestion is None or suggestion.suggestion_type != "schedule":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="日程建议不存在")
    return suggestion


def _confirmed_profile(db: Session, customer_id: int):
    profile = profile_dao.get_current_confirmed(db, customer_id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="请先确认一份客户画像")
    return profile


def generate_schedule_suggestion(db: Session, customer_id: int, current_user: User) -> AISuggestion:
    """兼容旧日程 URL，但实际复用统一 LangGraph/Provider 入口。"""

    from app.services.ai_workflow_service import run_customer_ai_workflow

    # 日程建议仍要求已确认画像；工作流会在缺少画像时先停在人工确认点。
    result = run_customer_ai_workflow(
        db,
        customer_id,
        current_user,
        workflow_goal="schedule",
        force_sync=True,
    )
    suggestion_ids = result.get("suggestion_ids")
    if result.get("status") == "failed":
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=result.get("error") or "AI 日程建议生成失败")
    if not isinstance(suggestion_ids, list) or not suggestion_ids:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="请先确认一份客户画像")
    suggestion = suggestion_dao.get_by_id(db, customer_id, int(suggestion_ids[0]))
    if suggestion is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="AI 日程建议不存在")
    return suggestion


def persist_graph_schedule_suggestion(
    db: Session,
    customer_id: int,
    actor_user_id: int,
    payload: dict[str, object],
) -> AISuggestion:
    """保存 LangGraph 日程草稿；人工确认前不创建 schedules 正式记录。"""

    current_user = db.get(User, actor_user_id)
    if current_user is None or not current_user.is_active:
        raise ValueError("active actor user is required")
    get_customer_or_404(db, customer_id, current_user, "update")
    profile = _confirmed_profile(db, customer_id)

    content = payload.get("content")
    evidence = payload.get("evidence", [])
    if not isinstance(content, dict) or not content:
        raise ValueError("schedule suggestion content is required")
    if not isinstance(evidence, list):
        raise ValueError("schedule suggestion evidence must be a list")

    suggestion = AISuggestion(
        customer_id=customer_id,
        user_id=current_user.id,
        profile_id=profile.id,
        suggestion_type="schedule",
        content_json=content,
        evidence_json=evidence,
        evidence_level=str(payload.get("evidence_level", "normal")),
        status=AISuggestionStatus.DRAFT.value,
        model_name=str(payload.get("model_name", "mock-rules")),
        model_version=str(payload.get("model_version", "1")),
        prompt_version="langgraph-schedule-v1",
    )
    suggestion_dao.add(db, suggestion)
    db.flush()
    append_audit_log(
        db,
        current_user,
        "customer.schedule_suggestion_generated",
        "ai_suggestion",
        str(suggestion.id),
        {
            "profile_id": profile.id,
            "status": suggestion.status,
            "workflow": "langgraph",
        },
    )
    db.commit()
    db.refresh(suggestion)
    return suggestion


def list_schedule_suggestions(db: Session, customer_id: int, current_user: User) -> list[AISuggestion]:
    get_customer_or_404(db, customer_id, current_user, "read")
    return suggestion_dao.list_by_customer_and_type(db, customer_id, "schedule")


def edit_schedule_suggestion(db: Session, customer_id: int, suggestion_id: int, current_user: User, payload: AISuggestionUpdate) -> AISuggestion:
    get_customer_or_404(db, customer_id, current_user, "update")
    suggestion = _get_schedule_suggestion_or_404(db, customer_id, suggestion_id)
    if suggestion.status not in ("draft", "edited"):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="只有草稿或已编辑日程建议可以修改")
    suggestion.edited_content_json = payload.content
    suggestion.status = AISuggestionStatus.EDITED.value
    record_feedback(db, suggestion, current_user, "edited", payload.content)
    append_audit_log(db, current_user, "customer.schedule_suggestion_edited", "ai_suggestion", str(suggestion.id), {"status": suggestion.status})
    db.commit()
    db.refresh(suggestion)
    return suggestion


def confirm_schedule_suggestion(db: Session, customer_id: int, suggestion_id: int, current_user: User) -> Schedule:
    get_customer_or_404(db, customer_id, current_user, "update")
    suggestion = _get_schedule_suggestion_or_404(db, customer_id, suggestion_id)
    if suggestion.status not in ("draft", "edited"):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="只有草稿或已编辑日程建议可以确认")
    content = suggestion.edited_content_json or suggestion.content_json
    try:
        due_at = datetime.fromisoformat(str(content["due_at"]))
        title = str(content["title"])
        priority = str(content.get("priority", "normal"))
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="日程建议内容格式无效") from exc
    if due_at.tzinfo is None:
        due_at = due_at.replace(tzinfo=timezone.utc)
    schedule = Schedule(customer_id=customer_id, user_id=current_user.id, suggestion_id=suggestion.id, title=title, description=content.get("description"), due_at=due_at, priority=priority, source="ai", status="confirmed", evidence_json=suggestion.evidence_json, confirmed_by=current_user.id, confirmed_at=datetime.now(timezone.utc))
    schedule_dao.add(db, schedule)
    db.flush()
    suggestion.status = AISuggestionStatus.ACCEPTED.value
    suggestion.decided_by = current_user.id
    suggestion.decided_at = datetime.now(timezone.utc)
    record_feedback(db, suggestion, current_user, "accepted", suggestion.edited_content_json)
    timeline_event_dao.add(db, TimelineEvent(customer_id=customer_id, operator_id=current_user.id, occurred_at=due_at, event_type="schedule_created", summary_encrypted=encrypt_text(f"已确认跟进日程：{title}"), source="system", reference_type="schedule", reference_id=str(schedule.id)))
    append_audit_log(db, current_user, "customer.schedule_confirmed", "schedule", str(schedule.id), {"suggestion_id": suggestion.id, "status": schedule.status, "wecom_calendar_synced": False})
    db.commit()
    db.refresh(schedule)
    return schedule


def reject_schedule_suggestion(db: Session, customer_id: int, suggestion_id: int, current_user: User) -> AISuggestion:
    """Reject a schedule draft without creating a formal schedule."""

    get_customer_or_404(db, customer_id, current_user, "update")
    suggestion = _get_schedule_suggestion_or_404(db, customer_id, suggestion_id)
    if suggestion.status not in ("draft", "edited"):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only a draft schedule suggestion can be rejected")
    suggestion.status = AISuggestionStatus.REJECTED.value
    suggestion.decided_by = current_user.id
    suggestion.decided_at = datetime.now(timezone.utc)
    record_feedback(db, suggestion, current_user, "rejected", suggestion.edited_content_json)
    append_audit_log(
        db,
        current_user,
        "customer.schedule_suggestion_rejected",
        "ai_suggestion",
        str(suggestion.id),
        {"status": suggestion.status},
    )
    db.commit()
    db.refresh(suggestion)
    return suggestion


def list_schedules(db: Session, customer_id: int, current_user: User) -> list[Schedule]:
    get_customer_or_404(db, customer_id, current_user, "read")
    return schedule_dao.list_by_customer(db, customer_id)


def update_schedule(db: Session, customer_id: int, schedule_id: int, current_user: User, payload: ScheduleUpdate) -> Schedule:
    get_customer_or_404(db, customer_id, current_user, "update")
    schedule = schedule_dao.get_by_id(db, customer_id, schedule_id)
    if schedule is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="日程不存在")
    if schedule.status not in ("confirmed",):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="当前状态不允许编辑日程")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(schedule, field, value)
    append_audit_log(db, current_user, "customer.schedule_edited", "schedule", str(schedule.id), {"status": schedule.status})
    db.commit()
    db.refresh(schedule)
    return schedule


_OUTCOME_LABELS = {
    "contacted": "已联系",
    "no_response": "未回应",
    "appointment": "已预约",
    "converted": "已成交",
    "lost": "明确流失",
    "other": "其他结果",
}


def change_schedule_status(
    db: Session,
    customer_id: int,
    schedule_id: int,
    current_user: User,
    new_status: str,
    completion: ScheduleCompletion | None = None,
) -> Schedule:
    get_customer_or_404(db, customer_id, current_user, "update")
    schedule = schedule_dao.get_by_id(db, customer_id, schedule_id)
    if schedule is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="日程不存在")
    if new_status == "completed" and schedule.status != "confirmed":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="只有已确认日程可以完成")
    if new_status == "cancelled" and schedule.status not in ("confirmed",):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="当前状态不允许取消日程")
    schedule.status = new_status
    if new_status == "completed":
        # 只有人工提交的结果才进入业务事实和客户时间线；不自动改变客户阶段。
        result = completion or ScheduleCompletion()
        schedule.outcome = result.outcome
        schedule.completion_note = result.completion_note.strip() if result.completion_note else None
        schedule.completed_at = datetime.now(timezone.utc)
        summary = f"完成跟进日程《{schedule.title}》：{_OUTCOME_LABELS[result.outcome]}"
        if schedule.completion_note:
            summary += f"；备注：{schedule.completion_note}"
        timeline_event_dao.add(
            db,
            TimelineEvent(
                customer_id=customer_id,
                operator_id=current_user.id,
                occurred_at=schedule.completed_at,
                event_type="schedule_completed",
                summary_encrypted=encrypt_text(summary),
                source="manual",
                reference_type="schedule",
                reference_id=str(schedule.id),
            ),
        )
        audit_detail = {"status": new_status, "outcome": result.outcome}
    else:
        audit_detail = {"status": new_status}
    append_audit_log(db, current_user, f"customer.schedule_{new_status}", "schedule", str(schedule.id), audit_detail)
    db.commit()
    db.refresh(schedule)
    return schedule
