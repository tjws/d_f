from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.tag import CustomerTagRead, TagRead
from app.services.tag_service import confirm_customer_tag, generate_tag_suggestions, list_customer_tags, list_tags, reject_customer_tag

router = APIRouter(tags=["tags"])


@router.get("/tags", response_model=list[TagRead])
def get_tags(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return list_tags(db)


def _read(customer_tag) -> CustomerTagRead:
    return CustomerTagRead(id=customer_tag.id, customer_id=customer_tag.customer_id, tag=customer_tag.tag, source=customer_tag.source, status=customer_tag.status, evidence=customer_tag.evidence_json, created_by=customer_tag.created_by, confirmed_by=customer_tag.confirmed_by, created_at=customer_tag.created_at, confirmed_at=customer_tag.confirmed_at)


@router.post("/customers/{customer_id}/tags/suggestions", response_model=list[CustomerTagRead])
def create_tag_suggestions(customer_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return [_read(customer_tag) for customer_tag in generate_tag_suggestions(db, customer_id, current_user)]


@router.get("/customers/{customer_id}/tags", response_model=list[CustomerTagRead])
def get_customer_tags(customer_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return [_read(customer_tag) for customer_tag in list_customer_tags(db, customer_id, current_user)]


@router.post("/customers/{customer_id}/tags/{customer_tag_id}/confirm", response_model=CustomerTagRead)
def confirm_tag(customer_id: int, customer_tag_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _read(confirm_customer_tag(db, customer_id, customer_tag_id, current_user))


@router.post("/customers/{customer_id}/tags/{customer_tag_id}/reject", response_model=CustomerTagRead)
def reject_tag(customer_id: int, customer_tag_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _read(reject_customer_tag(db, customer_id, customer_tag_id, current_user))
