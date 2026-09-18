from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.course_order import CourseOrder
from app.models.customer import Customer
from app.models.service_ticket import ServiceTicket
from app.models.user import User


class BusinessDashboardDAO:
    """只负责按时间窗口读取经营事实，指标解释放在 Service 层。"""

    def customers_in_window(self, db: Session, start: datetime, end: datetime) -> list[Customer]:
        return list(
            db.scalars(
                select(Customer)
                .where(Customer.created_at >= start, Customer.created_at < end)
                .order_by(Customer.created_at.desc())
            ).all()
        )

    def all_customers(self, db: Session) -> list[Customer]:
        return list(db.scalars(select(Customer)).all())

    def orders_in_window(self, db: Session, start: datetime, end: datetime) -> list[CourseOrder]:
        return list(
            db.scalars(
                select(CourseOrder)
                .where(CourseOrder.ordered_at >= start, CourseOrder.ordered_at < end)
                .order_by(CourseOrder.ordered_at.desc())
            ).all()
        )

    def tickets_in_window(self, db: Session, start: datetime, end: datetime) -> list[ServiceTicket]:
        return list(
            db.scalars(
                select(ServiceTicket)
                .where(ServiceTicket.opened_at >= start, ServiceTicket.opened_at < end)
                .order_by(ServiceTicket.opened_at.desc())
            ).all()
        )

    def active_sales_users(self, db: Session) -> list[User]:
        return list(
            db.scalars(
                select(User)
                .where(User.is_active.is_(True), User.role.in_(("sales", "manager")))
                .order_by(User.id)
            ).all()
        )
