from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.dao.customer_tag_dao import CustomerTagDAO
from app.dao.tag_dao import TagDAO
from app.models.customer_tag import CustomerTag
from app.models.tag import Tag
from app.models.user import User
from app.services.audit_log_service import append_audit_log
from app.services.customer_service import get_customer_or_404
from app.services.ai_suggestion_feedback_service import record_target_feedback


tag_dao = TagDAO()
customer_tag_dao = CustomerTagDAO()


def list_tags(db: Session) -> list[Tag]:
    return tag_dao.list_active(db)


def list_customer_tags(db: Session, customer_id: int, current_user: User) -> list[CustomerTag]:
    get_customer_or_404(db, customer_id, current_user, "read")
    return customer_tag_dao.list_by_customer(db, customer_id)


def _ensure_tag(db: Session, key: str, name: str, category: str, description: str, color: str) -> Tag:
    tag = tag_dao.get_by_key(db, key)
    if tag is not None:
        return tag
    tag = Tag(key=key, name=name, category=category, description=description, color=color, status="active")
    tag_dao.add(db, tag)
    db.flush()
    return tag


def _persist_tag_candidates(
    db: Session,
    customer_id: int,
    current_user: User,
    candidates: list[dict[str, object]],
    model_name: str,
    model_version: str,
    workflow: str | None = None,
) -> list[CustomerTag]:
    """把标签候选项和审计日志写入同一事务，供普通接口和 Graph 共用。"""

    suggestions: list[CustomerTag] = []
    for candidate in candidates:
        required_keys = {"key", "name", "category", "description", "color"}
        if not required_keys.issubset(candidate):
            raise ValueError("tag candidate is incomplete")
        key = str(candidate["key"])
        name = str(candidate["name"])
        category = str(candidate["category"])
        description = str(candidate["description"])
        color = str(candidate["color"])
        evidence = candidate.get("evidence", [])
        if not isinstance(evidence, list):
            raise ValueError("tag evidence must be a list")

        tag = _ensure_tag(db, key, name, category, description, color)
        previous = customer_tag_dao.get_latest_for_tag(db, customer_id, tag.id)
        if previous is not None and previous.status in {"suggested", "confirmed"}:
            suggestions.append(previous)
            continue

        customer_tag = CustomerTag(
            customer_id=customer_id,
            tag_id=tag.id,
            source="ai",
            status="suggested",
            evidence_json=evidence,
            created_by=current_user.id,
        )
        customer_tag_dao.add(db, customer_tag)
        db.flush()
        detail = {
            "customer_id": customer_id,
            "tag_key": key,
            "status": customer_tag.status,
            "model_name": model_name,
            "model_version": model_version,
        }
        if workflow is not None:
            detail["workflow"] = workflow
        append_audit_log(
            db,
            current_user,
            "customer.ai_tags_generated",
            "customer_tag",
            str(customer_tag.id),
            detail,
        )
        suggestions.append(customer_tag)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="客户标签建议发生并发冲突",
        ) from None
    return [customer_tag_dao.get_by_id(db, customer_id, item.id) for item in suggestions]


def generate_tag_suggestions(db: Session, customer_id: int, current_user: User) -> list[CustomerTag]:
    """兼容旧标签 URL，但实际复用统一 LangGraph/Provider 入口。"""

    from app.services.ai_workflow_service import run_customer_ai_workflow

    result = run_customer_ai_workflow(
        db,
        customer_id,
        current_user,
        workflow_goal="tag",
        force_sync=True,
    )
    if result.get("status") == "failed":
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=result.get("error") or "AI 标签建议生成失败")
    tag_ids = result.get("customer_tag_ids")
    if not isinstance(tag_ids, list) or not tag_ids:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="请先确认一份客户画像")
    result_tags: list[CustomerTag] = []
    for tag_id in tag_ids:
        tag = customer_tag_dao.get_by_id(db, customer_id, int(tag_id))
        if tag is not None:
            result_tags.append(tag)
    return result_tags


def persist_graph_tag_suggestions(
    db: Session,
    customer_id: int,
    actor_user_id: int,
    payload: dict[str, object],
) -> list[CustomerTag]:
    """保存 Graph 生成的待确认标签，并记录其工作流来源。"""

    current_user = db.get(User, actor_user_id)
    if current_user is None or not current_user.is_active:
        raise ValueError("active actor user is required")
    get_customer_or_404(db, customer_id, current_user, "update")

    candidates = payload.get("candidates")
    if not isinstance(candidates, list):
        raise ValueError("tag candidates are required")
    normalized_candidates = [item for item in candidates if isinstance(item, dict)]
    if len(normalized_candidates) != len(candidates):
        raise ValueError("tag candidates must be objects")
    return _persist_tag_candidates(
        db,
        customer_id,
        current_user,
        normalized_candidates,
        str(payload.get("model_name", "mock-rules")),
        str(payload.get("model_version", "1")),
        workflow="langgraph",
    )


def confirm_customer_tag(db: Session, customer_id: int, customer_tag_id: int, current_user: User) -> CustomerTag:
    get_customer_or_404(db, customer_id, current_user, "update")
    customer_tag = customer_tag_dao.get_by_id(db, customer_id, customer_tag_id)
    if customer_tag is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="客户标签不存在")
    if customer_tag.status != "suggested":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="只有待确认标签建议可以确认")
    customer_tag.status = "confirmed"
    customer_tag.confirmed_by = current_user.id
    customer_tag.confirmed_at = datetime.now(timezone.utc)
    record_target_feedback(db, customer_id, current_user, "tag", str(customer_tag.id), "accepted")
    append_audit_log(db, current_user, "customer.ai_tag_confirmed", "customer_tag", str(customer_tag.id), {"tag_id": customer_tag.tag_id, "status": customer_tag.status})
    db.commit()
    db.refresh(customer_tag)
    return customer_tag


def reject_customer_tag(db: Session, customer_id: int, customer_tag_id: int, current_user: User) -> CustomerTag:
    get_customer_or_404(db, customer_id, current_user, "update")
    customer_tag = customer_tag_dao.get_by_id(db, customer_id, customer_tag_id)
    if customer_tag is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="客户标签不存在")
    if customer_tag.status != "suggested":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="只有待确认标签建议可以拒绝")
    customer_tag.status = "rejected"
    customer_tag.confirmed_by = current_user.id
    customer_tag.confirmed_at = datetime.now(timezone.utc)
    record_target_feedback(db, customer_id, current_user, "tag", str(customer_tag.id), "rejected")
    append_audit_log(db, current_user, "customer.ai_tag_rejected", "customer_tag", str(customer_tag.id), {"tag_id": customer_tag.tag_id, "status": customer_tag.status})
    db.commit()
    db.refresh(customer_tag)
    return customer_tag
