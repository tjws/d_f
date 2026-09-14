from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.dao.customer_tag_dao import CustomerTagDAO
from app.dao.tag_dao import TagDAO
from app.models.customer import Customer
from app.models.customer_tag import CustomerTag
from app.models.customer_profile import CustomerProfile
from app.models.tag import Tag
from app.models.user import User
from app.services.audit_log_service import append_audit_log
from app.services.customer_service import get_customer_or_404


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


def _suggestion_candidates(customer: Customer, profile: CustomerProfile | None) -> list[tuple[str, str, str, str, str]]:
    candidates = []
    if customer.interested_subject:
        # 标签 key 必须稳定，不能直接把任意用户输入拼进系统标识。
        subject_keys = {"数学": "subject_math", "英语": "subject_english", "语文": "subject_chinese", "物理": "subject_physics", "化学": "subject_chemistry"}
        subject_key = subject_keys.get(customer.interested_subject, "subject_other")
        candidates.append((subject_key, f"{customer.interested_subject}兴趣", "学习兴趣", "客户明确关注的学科", "#3B82F6"))
    if customer.stage == "following_up":
        candidates.append(("follow_up_active", "需要持续跟进", "销售阶段", "客户处于跟进阶段", "#F59E0B"))
    if profile is not None and profile.dimensions_json.get("student_count", 0) > 0:
        candidates.append(("has_student_profile", "已有学生资料", "资料完整度", "客户已有学生资料可供分析", "#10B981"))
    return candidates


def generate_tag_suggestions(db: Session, customer_id: int, current_user: User) -> list[CustomerTag]:
    customer = get_customer_or_404(db, customer_id, current_user, "update")
    from app.dao.customer_profile_dao import CustomerProfileDAO

    profile = CustomerProfileDAO().get_current_confirmed(db, customer_id)
    suggestions = []
    for key, name, category, description, color in _suggestion_candidates(customer, profile):
        tag = _ensure_tag(db, key, name, category, description, color)
        previous = customer_tag_dao.get_latest_for_tag(db, customer_id, tag.id)
        if previous is not None and previous.status in {"suggested", "confirmed"}:
            suggestions.append(customer_tag_dao.get_by_id(db, customer_id, previous.id))
            continue
        customer_tag = CustomerTag(customer_id=customer_id, tag_id=tag.id, source="ai", status="suggested", evidence_json=[{"source_type": "customer_profile" if profile else "customer", "source_id": str(profile.id) if profile else str(customer.id), "fact": description}], created_by=current_user.id)
        customer_tag_dao.add(db, customer_tag)
        db.flush()
        append_audit_log(db, current_user, "customer.ai_tags_generated", "customer_tag", str(customer_tag.id), {"customer_id": customer_id, "tag_key": key, "status": customer_tag.status})
        suggestions.append(customer_tag)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="客户标签建议发生并发冲突") from None
    return [customer_tag_dao.get_by_id(db, customer_id, item.id) for item in suggestions]


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
    append_audit_log(db, current_user, "customer.ai_tag_rejected", "customer_tag", str(customer_tag.id), {"tag_id": customer_tag.tag_id, "status": customer_tag.status})
    db.commit()
    db.refresh(customer_tag)
    return customer_tag
