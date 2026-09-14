from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.customer_profile import CustomerProfileRead, CustomerProfileUpdate
from app.services.customer_profile_service import confirm_profile, generate_draft, list_profiles, reject_profile, update_draft

router = APIRouter(prefix="/customers/{customer_id}/profiles", tags=["customer-profiles"])


def _read(profile) -> CustomerProfileRead:
    return CustomerProfileRead(id=profile.id, customer_id=profile.customer_id, version=profile.version, status=profile.status, dimensions=profile.dimensions_json, evidence=profile.evidence_json, model_name=profile.model_name, model_version=profile.model_version, prompt_version=profile.prompt_version, confirmed_by=profile.confirmed_by, confirmed_at=profile.confirmed_at, created_at=profile.created_at)


@router.post("/draft", response_model=CustomerProfileRead, status_code=status.HTTP_201_CREATED)
def create_profile_draft(customer_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _read(generate_draft(db, customer_id, current_user))


@router.get("", response_model=list[CustomerProfileRead])
def get_profiles(customer_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return [_read(profile) for profile in list_profiles(db, customer_id, current_user)]


@router.patch("/{profile_id}", response_model=CustomerProfileRead)
def edit_profile_draft(customer_id: int, profile_id: int, payload: CustomerProfileUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _read(update_draft(db, customer_id, profile_id, current_user, payload))


@router.post("/{profile_id}/confirm", response_model=CustomerProfileRead)
def confirm_profile_draft(customer_id: int, profile_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _read(confirm_profile(db, customer_id, profile_id, current_user))


@router.post("/{profile_id}/reject", response_model=CustomerProfileRead)
def reject_profile_draft(customer_id: int, profile_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _read(reject_profile(db, customer_id, profile_id, current_user))
