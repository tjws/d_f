from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.models.schedule import Schedule


class ScheduleDAO:
    def get_by_id(self, db: Session, customer_id: int, schedule_id: int) -> Schedule | None:
        return db.scalar(select(Schedule).where(Schedule.customer_id == customer_id, Schedule.id == schedule_id))

    def list_by_customer(self, db: Session, customer_id: int) -> list[Schedule]:
        return list(db.scalars(select(Schedule).where(Schedule.customer_id == customer_id).order_by(Schedule.due_at.asc(), Schedule.id.desc())).all())

    def list_completed_by_customer(self, db: Session, customer_id: int, limit: int = 5) -> list[Schedule]:
        """只返回已由人工确认完成的日程，供后续 AI 建议参考。"""

        return list(
            db.scalars(
                select(Schedule)
                .where(Schedule.customer_id == customer_id, Schedule.status == "completed")
                .order_by(desc(Schedule.completed_at), desc(Schedule.id))
                .limit(limit)
            ).all()
        )

    def add(self, db: Session, schedule: Schedule) -> None:
        db.add(schedule)
