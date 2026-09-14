from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.models.customer_profile import CustomerProfile


class CustomerProfileDAO:
    """画像版本的查询和写入；事务仍由 Customer Profile Service 管理。"""

    def next_version(self, db: Session, customer_id: int) -> int:
        latest = db.scalar(select(func.max(CustomerProfile.version)).where(CustomerProfile.customer_id == customer_id))
        return (latest or 0) + 1

    def get_by_id(self, db: Session, customer_id: int, profile_id: int) -> CustomerProfile | None:
        return db.scalar(select(CustomerProfile).where(CustomerProfile.customer_id == customer_id, CustomerProfile.id == profile_id))

    def list_by_customer(self, db: Session, customer_id: int) -> list[CustomerProfile]:
        return list(db.scalars(select(CustomerProfile).where(CustomerProfile.customer_id == customer_id).order_by(CustomerProfile.version.desc())).all())

    def get_current_confirmed(self, db: Session, customer_id: int) -> CustomerProfile | None:
        return db.scalar(select(CustomerProfile).where(CustomerProfile.customer_id == customer_id, CustomerProfile.status == "confirmed").order_by(CustomerProfile.version.desc()))

    def archive_confirmed(self, db: Session, customer_id: int, except_profile_id: int) -> None:
        db.execute(update(CustomerProfile).where(CustomerProfile.customer_id == customer_id, CustomerProfile.id != except_profile_id, CustomerProfile.status == "confirmed").values(status="archived"))

    def add(self, db: Session, profile: CustomerProfile) -> None:
        db.add(profile)
