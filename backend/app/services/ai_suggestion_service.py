from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.dao.ai_suggestion_dao import AISuggestionDAO
from app.dao.chat_message_dao import ChatMessageDAO
from app.dao.customer_profile_dao import CustomerProfileDAO
from app.dao.timeline_event_dao import TimelineEventDAO
from app.models.ai_suggestion import AISuggestion
from app.models.user import User
from app.schemas.ai_suggestion import AISuggestionStatus, AISuggestionUpdate
from app.services.audit_log_service import append_audit_log
from app.services.customer_service import get_customer_or_404
from app.services.reply_generator import generate_mock_reply


suggestion_dao = AISuggestionDAO()
profile_dao = CustomerProfileDAO()
chat_message_dao = ChatMessageDAO()
timeline_event_dao = TimelineEventDAO()


def _get_suggestion_or_404(db: Session, customer_id: int, suggestion_id: int) -> AISuggestion:
    suggestion = suggestion_dao.get_by_id(db, customer_id, suggestion_id)
    if suggestion is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AI 建议不存在")
    return suggestion


def _current_confirmed_profile(db: Session, customer_id: int):
    profile = profile_dao.get_current_confirmed(db, customer_id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="请先确认一份客户画像")
    return profile


def generate_reply_draft(db: Session, customer_id: int, current_user: User) -> AISuggestion:
    customer = get_customer_or_404(db, customer_id, current_user, "update")
    profile = _current_confirmed_profile(db, customer_id)
    content, evidence, evidence_level = generate_mock_reply(customer, profile, chat_message_dao.list_by_customer(db, customer_id), timeline_event_dao.list_by_customer(db, customer_id))
    suggestion = AISuggestion(customer_id=customer_id, user_id=current_user.id, profile_id=profile.id, suggestion_type="reply", content_json=content, evidence_json=evidence, evidence_level=evidence_level, status=AISuggestionStatus.DRAFT.value, model_name="mock-rules", model_version="1", prompt_version="reply-v1")
    suggestion_dao.add(db, suggestion)
    db.flush()
    append_audit_log(db, current_user, "customer.ai_reply_generated", "ai_suggestion", str(suggestion.id), {"customer_id": customer_id, "profile_id": profile.id, "status": suggestion.status})
    db.commit()
    db.refresh(suggestion)
    return suggestion


def list_suggestions(db: Session, customer_id: int, current_user: User) -> list[AISuggestion]:
    get_customer_or_404(db, customer_id, current_user, "read")
    return suggestion_dao.list_by_customer(db, customer_id)


def edit_suggestion(db: Session, customer_id: int, suggestion_id: int, current_user: User, payload: AISuggestionUpdate) -> AISuggestion:
    get_customer_or_404(db, customer_id, current_user, "update")
    suggestion = _get_suggestion_or_404(db, customer_id, suggestion_id)
    if suggestion.status not in (AISuggestionStatus.DRAFT.value, AISuggestionStatus.EDITED.value):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="只有草稿或已编辑建议可以修改")
    suggestion.edited_content_json = payload.content
    suggestion.status = AISuggestionStatus.EDITED.value
    append_audit_log(db, current_user, "customer.ai_reply_edited", "ai_suggestion", str(suggestion.id), {"status": suggestion.status})
    db.commit()
    db.refresh(suggestion)
    return suggestion


def accept_suggestion(db: Session, customer_id: int, suggestion_id: int, current_user: User) -> AISuggestion:
    get_customer_or_404(db, customer_id, current_user, "update")
    suggestion = _get_suggestion_or_404(db, customer_id, suggestion_id)
    if suggestion.status not in (AISuggestionStatus.DRAFT.value, AISuggestionStatus.EDITED.value):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="只有草稿或已编辑建议可以接受")
    suggestion.status = AISuggestionStatus.ACCEPTED.value
    suggestion.decided_by = current_user.id
    suggestion.decided_at = datetime.now(timezone.utc)
    append_audit_log(db, current_user, "customer.ai_reply_accepted", "ai_suggestion", str(suggestion.id), {"status": suggestion.status, "sent": False})
    db.commit()
    db.refresh(suggestion)
    return suggestion


def reject_suggestion(db: Session, customer_id: int, suggestion_id: int, current_user: User) -> AISuggestion:
    get_customer_or_404(db, customer_id, current_user, "update")
    suggestion = _get_suggestion_or_404(db, customer_id, suggestion_id)
    if suggestion.status not in (AISuggestionStatus.DRAFT.value, AISuggestionStatus.EDITED.value):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="只有草稿或已编辑建议可以拒绝")
    suggestion.status = AISuggestionStatus.REJECTED.value
    suggestion.decided_by = current_user.id
    suggestion.decided_at = datetime.now(timezone.utc)
    append_audit_log(db, current_user, "customer.ai_reply_rejected", "ai_suggestion", str(suggestion.id), {"status": suggestion.status})
    db.commit()
    db.refresh(suggestion)
    return suggestion


def persist_graph_reply_draft(
    db: Session,
    customer_id: int,
    actor_user_id: int,
    payload: dict,
) -> AISuggestion:
    """保存 LangGraph 生成的回复草稿，并与审计日志共用一个事务。"""

    current_user = db.get(User, actor_user_id)
    if current_user is None or not current_user.is_active:
        raise ValueError("active actor user is required")

    get_customer_or_404(db, customer_id, current_user, "update")
    profile = _current_confirmed_profile(db, customer_id)

    content = payload.get("content")
    if not isinstance(content, dict) or not content:
        raise ValueError("suggestion content is required")

    suggestion = AISuggestion(
        customer_id=customer_id,
        user_id=current_user.id,
        profile_id=profile.id,
        suggestion_type=str(payload.get("suggestion_type", "reply")),
        content_json=content,
        evidence_json=payload.get("evidence", []),
        evidence_level=str(payload.get("evidence_level", "normal")),
        status=AISuggestionStatus.DRAFT.value,
        model_name=str(payload.get("model_name", "mock-rules")),
        model_version=str(payload.get("model_version", "1")),
        prompt_version="langgraph-reply-v1",
    )
    suggestion_dao.add(db, suggestion)
    db.flush()
    append_audit_log(
        db,
        current_user,
        "customer.ai_reply_generated",
        "ai_suggestion",
        str(suggestion.id),
        {"customer_id": customer_id, "status": suggestion.status, "workflow": "langgraph"},
    )
    db.commit()
    db.refresh(suggestion)
    return suggestion
