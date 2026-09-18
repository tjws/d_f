from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.course_order import CourseOrder
from app.models.customer import Customer
from app.models.service_ticket import ServiceTicket
from app.models.user import User


class AdminOperationsDAO:
    """读取管理层需要回溯的订单和工单，并保留客户数据范围过滤条件。"""

    def list_orders(self, db: Session, scope_filters: list, status_filter: str | None, limit: int):
        statement = select(CourseOrder, Customer, User).join(Customer, Customer.id == CourseOrder.customer_id).outerjoin(User, User.id == Customer.owner_id)
        if scope_filters:
            statement = statement.where(*scope_filters)
        if status_filter:
            statement = statement.where(CourseOrder.status == status_filter)
        return list(db.execute(statement.order_by(CourseOrder.ordered_at.desc(), CourseOrder.id.desc()).limit(limit)).all())

    def list_tickets(self, db: Session, scope_filters: list, status_filter: str | None, limit: int):
        statement = select(ServiceTicket, Customer, User).join(Customer, Customer.id == ServiceTicket.customer_id).outerjoin(User, User.id == Customer.owner_id)
        if scope_filters:
            statement = statement.where(*scope_filters)
        if status_filter:
            statement = statement.where(ServiceTicket.status == status_filter)
        return list(db.execute(statement.order_by(ServiceTicket.opened_at.desc(), ServiceTicket.id.desc()).limit(limit)).all())
