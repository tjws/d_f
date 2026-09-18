"""“我的待办”中正式日程的只读查询。"""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.customer import Customer
from app.models.schedule import Schedule


class MyWorkDAO:
    """只查询当前执行人尚未完成的正式日程。"""

    def list_open_schedules(self, db: Session, user_id: int, customer_filters: list):
        statement = (
            select(Schedule, Customer.name, Customer.stage)
            .join(Customer, Customer.id == Schedule.customer_id)
            .where(
                Schedule.user_id == user_id,
                Schedule.status == "confirmed",
                *customer_filters,
            )
            .order_by(Schedule.due_at.asc(), Schedule.id.desc())
        )
        return list(db.execute(statement).all())
