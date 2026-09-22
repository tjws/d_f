"""把 AI 草稿聚合成当前用户可见的待处理工作项。"""

from datetime import datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.dao.pending_action_dao import PendingActionDAO
from app.models.ai_suggestion import AISuggestion
from app.models.customer_profile import CustomerProfile
from app.models.customer_tag import CustomerTag
from app.models.chat_message import ChatMessage
from app.models.user import User
from app.schemas.ai_suggestion import AISuggestionUpdate
from app.schemas.customer_profile import CustomerProfileUpdate
from app.schemas.pending_action import PendingActionDecision, PendingActionType
from app.services.customer_service import customer_scope_filters
from app.services.ai_suggestion_service import accept_suggestion, edit_suggestion, reject_suggestion
from app.services.customer_profile_service import confirm_profile, reject_profile, update_draft
from app.services.schedule_service import confirm_schedule_suggestion, edit_schedule_suggestion, reject_schedule_suggestion
from app.services.tag_service import confirm_customer_tag, reject_customer_tag
from app.services.audit_log_service import append_audit_log
from app.services.customer_service import get_customer_or_404


pending_action_dao = PendingActionDAO()
_HISTORICAL_REVIEW_AFTER = timedelta(days=7)
_DISPLAY_TIMEZONE = ZoneInfo("Asia/Shanghai")


def dismiss_historical_reply(db: Session, current_user: User, resource_id: int) -> dict[str, object]:
    """将超过七天且未完成的回复草稿标记为 expired，保留审计和原始建议。"""

    resource = db.get(AISuggestion, resource_id)
    if resource is None or resource.suggestion_type != "reply":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AI 回复建议不存在")
    get_customer_or_404(db, resource.customer_id, current_user, "update")
    created_at = resource.created_at if resource.created_at.tzinfo else resource.created_at.replace(tzinfo=timezone.utc)
    historical_before = datetime.now(timezone.utc).astimezone(_DISPLAY_TIMEZONE).date() - _HISTORICAL_REVIEW_AFTER
    if created_at.astimezone(_DISPLAY_TIMEZONE).date() > historical_before:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="仅可关闭满七日的历史回复草稿")
    return dismiss_reply(db, current_user, resource_id, reason="historical_workbench_dismissed")


def dismiss_reply(
    db: Session, current_user: User, resource_id: int, reason: str = "workbench_dismissed"
) -> dict[str, object]:
    """关闭不再需要的回复建议：不发送消息、不删除内容，保留审计链路。"""

    resource = db.get(AISuggestion, resource_id)
    if resource is None or resource.suggestion_type != "reply":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AI 回复建议不存在")
    get_customer_or_404(db, resource.customer_id, current_user, "update")
    if resource.status not in {"draft", "edited", "accepted"}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="该建议已经关闭")

    resource.status = "expired"
    resource.decided_by = current_user.id
    resource.decided_at = datetime.now(timezone.utc)
    append_audit_log(
        db, current_user, "customer.ai_reply_expired", "ai_suggestion", str(resource.id),
        {"reason": reason, "sent": False},
    )
    db.commit()
    return {"action_type": "reply", "resource_id": resource.id, "status": resource.status, "closed": True}


def review_pending_action(
    db: Session,
    current_user: User,
    action_type: PendingActionType,
    resource_id: int,
    payload: PendingActionDecision,
) -> dict[str, object]:
    """Route a human decision to the owning domain service; no action sends a message."""

    if payload.action == "edited" and not payload.content:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Edited content is required")

    if action_type == "profile":
        resource = db.get(CustomerProfile, resource_id)
        if resource is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile draft not found")
        if payload.action == "edited":
            update_draft(db, resource.customer_id, resource.id, current_user, CustomerProfileUpdate(dimensions=payload.content or {}))
        elif payload.action == "accepted":
            confirm_profile(db, resource.customer_id, resource.id, current_user)
        else:
            reject_profile(db, resource.customer_id, resource.id, current_user)
        current_status = db.get(CustomerProfile, resource_id).status
    elif action_type in {"reply", "schedule"}:
        resource = db.get(AISuggestion, resource_id)
        if resource is None or resource.suggestion_type != action_type:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AI suggestion not found")
        if payload.action == "edited":
            if action_type == "reply":
                edit_suggestion(db, resource.customer_id, resource.id, current_user, AISuggestionUpdate(content=payload.content or {}))
            else:
                edit_schedule_suggestion(db, resource.customer_id, resource.id, current_user, AISuggestionUpdate(content=payload.content or {}))
        elif payload.action == "accepted":
            if action_type == "reply":
                accept_suggestion(db, resource.customer_id, resource.id, current_user)
            else:
                confirm_schedule_suggestion(db, resource.customer_id, resource.id, current_user)
        else:
            if action_type == "reply":
                reject_suggestion(db, resource.customer_id, resource.id, current_user)
            else:
                reject_schedule_suggestion(db, resource.customer_id, resource.id, current_user)
        current_status = db.get(AISuggestion, resource_id).status
    else:
        resource = db.get(CustomerTag, resource_id)
        if resource is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer tag suggestion not found")
        if payload.action == "edited":
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Tag suggestions do not support editing")
        if payload.action == "accepted":
            confirm_customer_tag(db, resource.customer_id, resource.id, current_user)
        else:
            reject_customer_tag(db, resource.customer_id, resource.id, current_user)
        current_status = db.get(CustomerTag, resource_id).status

    # 回复建议在“接受”后还要经过放入输入框并实际发送；只有发送消息已
    # 关联到 suggestion_id，才算完整关闭该人工待办。
    closed = current_status in {"confirmed", "rejected"}
    if action_type == "profile" and current_status == "accepted":
        closed = True
    if action_type == "reply" and current_status == "accepted":
        closed = db.scalar(
            select(ChatMessage.id).where(ChatMessage.suggestion_id == resource_id)
        ) is not None

    return {
        "action_type": action_type,
        "resource_id": resource_id,
        "action": payload.action,
        "status": current_status,
        "closed": closed,
    }


def _short_text(value: object, fallback: str) -> str:
    """工作台仅显示必要摘要，避免跨客户页面展开完整敏感 AI 内容。"""

    if isinstance(value, str) and value.strip():
        return value.strip().replace("\n", " ")[:120]
    return fallback


def _suggestion_summary(content: dict[str, Any], action_type: str) -> str:
    if action_type == "schedule":
        return _short_text(content.get("title"), "待人工确认的跟进日程")
    return _short_text(content.get("text"), "待人工确认的回复草稿")


def list_pending_actions(
    db: Session,
    current_user: User,
    action_type: str | None = None,
    limit: int = 100,
) -> list[dict[str, object]]:
    """按 customers.read 数据范围返回聚合项；前端不能自行拼接越权数据。"""

    customer_filters = customer_scope_filters(db, current_user, "read")
    items: list[dict[str, object]] = []
    wanted = action_type or "all"

    if wanted in {"all", "profile"}:
        for profile, customer_name, customer_stage in pending_action_dao.list_profiles(db, customer_filters):
            items.append(
                {
                    "id": f"profile:{profile.id}",
                    "resource_id": profile.id,
                    "action_type": "profile",
                    "customer_id": profile.customer_id,
                    "customer_name": customer_name,
                    "customer_stage": customer_stage,
                    "status": profile.status,
                    "title": f"客户画像草稿 v{profile.version}",
                    "summary": "请检查画像维度、证据和建议下一步，再确认或拒绝。",
                    "created_at": profile.created_at,
                }
            )

    if wanted in {"all", "reply", "schedule"}:
        for suggestion, customer_name, customer_stage in pending_action_dao.list_suggestions(db, customer_filters):
            if wanted not in {"all", suggestion.suggestion_type}:
                continue
            items.append(
                {
                    "id": f"{suggestion.suggestion_type}:{suggestion.id}",
                    "resource_id": suggestion.id,
                    "action_type": suggestion.suggestion_type,
                    "customer_id": suggestion.customer_id,
                    "customer_name": customer_name,
                    "customer_stage": customer_stage,
                    "status": suggestion.status,
                    "title": "回复建议" if suggestion.suggestion_type == "reply" else "跟进日程建议",
                    "summary": _suggestion_summary(suggestion.edited_content_json or suggestion.content_json, suggestion.suggestion_type),
                    "created_at": suggestion.created_at,
                }
            )

    if wanted in {"all", "tag"}:
        for customer_tag, tag, customer_name, customer_stage in pending_action_dao.list_tags(db, customer_filters):
            items.append(
                {
                    "id": f"tag:{customer_tag.id}",
                    "resource_id": customer_tag.id,
                    "action_type": "tag",
                    "customer_id": customer_tag.customer_id,
                    "customer_name": customer_name,
                    "customer_stage": customer_stage,
                    "status": customer_tag.status,
                    "title": f"标签建议：{tag.name}",
                    "summary": _short_text(tag.description, "请确认该标签是否适用于当前客户。"),
                    "created_at": customer_tag.created_at,
                }
            )

    items.sort(key=lambda item: item["created_at"], reverse=True)
    return items[:limit]
