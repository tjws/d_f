from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.permissions import require_permission
from app.db.session import get_db
from app.schemas.organization import OrganizationCreate, OrganizationRead
from app.services.organization_service import create_organization, list_organizations

router = APIRouter(prefix="/organizations", tags=["organizations"])


@router.get("", response_model=list[OrganizationRead])
def get_organizations(current_user=Depends(require_permission("organizations", "read")), db: Session = Depends(get_db)):
    return list_organizations(db)


@router.post("", response_model=OrganizationRead, status_code=status.HTTP_201_CREATED)
def add_organization(payload: OrganizationCreate, current_user=Depends(require_permission("organizations", "create")), db: Session = Depends(get_db)):
    return create_organization(db, current_user, payload)
