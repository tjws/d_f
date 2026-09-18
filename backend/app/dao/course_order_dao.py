from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.course_order import CourseOrder


class CourseOrderDAO:
    def get_by_id(self, db: Session, customer_id: int, order_id: int) -> CourseOrder | None:
        return db.scalar(select(CourseOrder).where(CourseOrder.customer_id == customer_id, CourseOrder.id == order_id))

    def get_by_external_id(self, db: Session, external_order_id: str) -> CourseOrder | None:
        return db.scalar(select(CourseOrder).where(CourseOrder.external_order_id == external_order_id))

    def list_by_customer(self, db: Session, customer_id: int) -> list[CourseOrder]:
        return list(db.scalars(select(CourseOrder).where(CourseOrder.customer_id == customer_id).order_by(CourseOrder.ordered_at.desc(), CourseOrder.id.desc())).all())

    def add(self, db: Session, order: CourseOrder) -> None:
        db.add(order)
