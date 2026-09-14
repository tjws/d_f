from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.customer_tag import CustomerTag


class CustomerTagDAO:
    def get_by_id(self, db: Session, customer_id: int, customer_tag_id: int) -> CustomerTag | None:
        return db.scalar(select(CustomerTag).options(joinedload(CustomerTag.tag)).where(CustomerTag.customer_id == customer_id, CustomerTag.id == customer_tag_id))

    def list_by_customer(self, db: Session, customer_id: int) -> list[CustomerTag]:
        return list(db.scalars(select(CustomerTag).options(joinedload(CustomerTag.tag)).where(CustomerTag.customer_id == customer_id).order_by(CustomerTag.created_at.desc(), CustomerTag.id.desc())).all())

    def get_latest_for_tag(self, db: Session, customer_id: int, tag_id: int) -> CustomerTag | None:
        return db.scalar(select(CustomerTag).where(CustomerTag.customer_id == customer_id, CustomerTag.tag_id == tag_id).order_by(CustomerTag.created_at.desc(), CustomerTag.id.desc()))

    def add(self, db: Session, customer_tag: CustomerTag) -> None:
        db.add(customer_tag)
