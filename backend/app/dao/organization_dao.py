from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.organization import Organization


class OrganizationDAO:
    def get_by_id(self, db: Session, organization_id: int) -> Organization | None:
        return db.get(Organization, organization_id)

    def list_all(self, db: Session) -> list[Organization]:
        return list(db.scalars(select(Organization).order_by(Organization.id)).all())

    def add(self, db: Session, organization: Organization) -> None:
        db.add(organization)
