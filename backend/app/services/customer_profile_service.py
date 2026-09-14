from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.dao.chat_message_dao import ChatMessageDAO
from app.dao.customer_profile_dao import CustomerProfileDAO
from app.dao.student_dao import StudentDAO
from app.dao.timeline_event_dao import TimelineEventDAO
from app.models.customer_profile import CustomerProfile
from app.models.user import User
from app.schemas.customer_profile import CustomerProfileStatus, CustomerProfileUpdate
from app.services.audit_log_service import append_audit_log
from app.services.customer_service import get_customer_or_404
from app.services.profile_generator import generate_mock_profile


profile_dao = CustomerProfileDAO()
student_dao = StudentDAO()
chat_message_dao = ChatMessageDAO()
timeline_event_dao = TimelineEventDAO()


def _get_profile_or_404(db: Session, customer_id: int, profile_id: int) -> CustomerProfile:
    profile = profile_dao.get_by_id(db, customer_id, profile_id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="客户画像不存在")
    return profile


def generate_draft(db: Session, customer_id: int, current_user: User) -> CustomerProfile:
    customer = get_customer_or_404(db, customer_id, current_user, "update")
    dimensions, evidence = generate_mock_profile(customer, student_dao.list_by_customer(db, customer_id), chat_message_dao.list_by_customer(db, customer_id), timeline_event_dao.list_by_customer(db, customer_id))
    profile = CustomerProfile(customer_id=customer_id, version=profile_dao.next_version(db, customer_id), status=CustomerProfileStatus.DRAFT.value, dimensions_json=dimensions, evidence_json=evidence, model_name="mock-rules", model_version="1", prompt_version="profile-v1")
    profile_dao.add(db, profile)
    db.flush()
    append_audit_log(db, current_user, "customer.profile_generated", "customer_profile", str(profile.id), {"customer_id": customer_id, "version": profile.version, "status": profile.status})
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
    append_audit_log(db, current_user, "customer.profile_rejected", "customer_profile", str(profile.id), {"version": profile.version})
    db.commit()
    db.refresh(profile)
    return profile
