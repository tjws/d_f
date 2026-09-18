from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.timeline_event import TimelineEvent


class TimelineEventDAO:
    def add(self, db: Session, event: TimelineEvent) -> None:
        db.add(event)

    def list_by_customer(self, db: Session, customer_id: int) -> list[TimelineEvent]:
        return list(db.scalars(select(TimelineEvent).where(TimelineEvent.customer_id == customer_id).order_by(TimelineEvent.occurred_at.desc(), TimelineEvent.id.desc())).all())

    def list_after_id(self, db: Session, customer_id: int, after_id: int = 0) -> list[TimelineEvent]:
        """按自增 ID 获取新增时间线事件。"""
        return list(
            db.scalars(
                select(TimelineEvent)
                .where(TimelineEvent.customer_id == customer_id, TimelineEvent.id > after_id)
                .order_by(TimelineEvent.id.asc())
            ).all()
        )
