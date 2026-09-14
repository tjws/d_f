from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.dao.organization_dao import OrganizationDAO
from app.models.organization import Organization
from app.models.user import User
from app.schemas.organization import OrganizationCreate
from app.services.audit_log_service import append_audit_log


organization_dao = OrganizationDAO()


def list_organizations(db: Session) -> list[Organization]:
    return organization_dao.list_all(db)


def create_organization(db: Session, current_user: User, payload: OrganizationCreate) -> Organization:
    parent = None
    if payload.parent_id is not None:
        parent = organization_dao.get_by_id(db, payload.parent_id)
        if parent is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="父组织不存在")
    organization = Organization(name=payload.name, type=payload.type, parent_id=payload.parent_id)
    organization_dao.add(db, organization)
    db.flush()
    parent_path = parent.path if parent is not None and parent.path else f"/{parent.id}" if parent is not None else ""
    organization.path = f"{parent_path}/{organization.id}" if parent_path else f"/{organization.id}"
    append_audit_log(db, current_user, "organization.created", "organization", str(organization.id), {"name": organization.name, "type": organization.type, "parent_id": organization.parent_id})
    db.commit()
    db.refresh(organization)
    return organization
