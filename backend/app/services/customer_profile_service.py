from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.dao.customer_profile_dao import CustomerProfileDAO
from app.models.customer_profile import CustomerProfile
from app.models.user import User
from app.schemas.customer_profile import CustomerProfileStatus, CustomerProfileUpdate
from app.services.audit_log_service import append_audit_log
from app.services.customer_service import get_customer_or_404
from app.services.ai_suggestion_feedback_service import record_target_feedback


profile_dao = CustomerProfileDAO()


def _get_profile_or_404(db: Session, customer_id: int, profile_id: int) -> CustomerProfile:
    profile = profile_dao.get_by_id(db, customer_id, profile_id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="客户画像不存在")
    return profile


def generate_draft(db: Session, customer_id: int, current_user: User) -> CustomerProfile:
    """兼容旧画像 URL，但实际转发到统一 LangGraph/Provider 入口。"""

    # 旧客户端仍需要同步拿到画像对象；force_sync 只影响这个兼容包装，
    # 不会改变新工作流默认使用队列的行为。
    from app.services.ai_workflow_service import run_customer_ai_workflow

    result = run_customer_ai_workflow(
        db,
        customer_id,
        current_user,
        workflow_goal="profile",
        force_sync=True,
    )
    profile_id = result.get("profile_id")
    if result.get("status") == "failed" or not isinstance(profile_id, int):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=result.get("error") or "AI 客户画像生成失败",
        )
    profile = profile_dao.get_by_id(db, customer_id, profile_id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="AI 画像草稿不存在")
    return profile


def persist_graph_profile_draft(
    db: Session,
    customer_id: int,
    actor_user_id: int,
    payload: dict[str, object],
) -> CustomerProfile:
    """保存 LangGraph 画像草稿，并与审计日志在同一事务中提交。"""

    current_user = db.get(User, actor_user_id)
    if current_user is None or not current_user.is_active:
        raise ValueError("active actor user is required")

    get_customer_or_404(db, customer_id, current_user, "update")
    dimensions = payload.get("dimensions")
    evidence = payload.get("evidence", [])
    if not isinstance(dimensions, dict) or not dimensions:
        raise ValueError("profile dimensions are required")
    if not isinstance(evidence, list):
        raise ValueError("profile evidence must be a list")

    profile = CustomerProfile(
        customer_id=customer_id,
        version=profile_dao.next_version(db, customer_id),
        status=CustomerProfileStatus.DRAFT.value,
        dimensions_json=dimensions,
        evidence_json=evidence,
        model_name=str(payload.get("model_name", "mock-rules")),
        model_version=str(payload.get("model_version", "1")),
        prompt_version="langgraph-profile-v1",
    )
    profile_dao.add(db, profile)
    db.flush()
    append_audit_log(
        db,
        current_user,
        "customer.profile_generated",
        "customer_profile",
        str(profile.id),
        {
            "customer_id": customer_id,
            "version": profile.version,
            "status": profile.status,
            "workflow": "langgraph",
        },
    )
    db.commit()
    db.refresh(profile)
    return profile


def list_profiles(db: Session, customer_id: int, current_user: User) -> list[CustomerProfile]:
    get_customer_or_404(db, customer_id, current_user, "read")
    return profile_dao.list_by_customer(db, customer_id)


def update_draft(db: Session, customer_id: int, profile_id: int, current_user: User, payload: CustomerProfileUpdate) -> CustomerProfile:
    get_customer_or_404(db, customer_id, current_user, "update")
    profile = _get_profile_or_404(db, customer_id, profile_id)
    if profile.status != CustomerProfileStatus.DRAFT.value:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="只有草稿画像可以编辑")
    profile.dimensions_json = payload.dimensions
    record_target_feedback(db, customer_id, current_user, "profile", str(profile.id), "edited", payload.dimensions)
    append_audit_log(db, current_user, "customer.profile_edited", "customer_profile", str(profile.id), {"version": profile.version})
    db.commit()
    db.refresh(profile)
    return profile


def confirm_profile(db: Session, customer_id: int, profile_id: int, current_user: User) -> CustomerProfile:
    get_customer_or_404(db, customer_id, current_user, "update")
    profile = _get_profile_or_404(db, customer_id, profile_id)
    if profile.status != CustomerProfileStatus.DRAFT.value:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="只有草稿画像可以确认")
    profile_dao.archive_confirmed(db, customer_id, profile.id)
    profile.status = CustomerProfileStatus.CONFIRMED.value
    profile.confirmed_by = current_user.id
    profile.confirmed_at = datetime.now(timezone.utc)
    record_target_feedback(db, customer_id, current_user, "profile", str(profile.id), "accepted", profile.dimensions_json)
    append_audit_log(db, current_user, "customer.profile_confirmed", "customer_profile", str(profile.id), {"version": profile.version})
    db.commit()
    db.refresh(profile)
    return profile


def reject_profile(db: Session, customer_id: int, profile_id: int, current_user: User) -> CustomerProfile:
    get_customer_or_404(db, customer_id, current_user, "update")
    profile = _get_profile_or_404(db, customer_id, profile_id)
    if profile.status != CustomerProfileStatus.DRAFT.value:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="只有草稿画像可以拒绝")
    profile.status = CustomerProfileStatus.REJECTED.value
    record_target_feedback(db, customer_id, current_user, "profile", str(profile.id), "rejected", profile.dimensions_json)
    append_audit_log(db, current_user, "customer.profile_rejected", "customer_profile", str(profile.id), {"version": profile.version})
    db.commit()
    db.refresh(profile)
    return profile
