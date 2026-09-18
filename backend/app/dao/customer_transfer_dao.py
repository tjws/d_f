from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.customer_transfer import CustomerTransfer


class CustomerTransferDAO:
    def add(self, db: Session, transfer: CustomerTransfer) -> None:
        db.add(transfer)

    def list_by_customer(self, db: Session, customer_id: int) -> list[CustomerTransfer]:
        return list(db.scalars(select(CustomerTransfer).where(CustomerTransfer.customer_id == customer_id).order_by(CustomerTransfer.id.desc())).all())
