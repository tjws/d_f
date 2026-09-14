from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.timeline_event import TimelineEvent


class TimelineEventDAO:
    def add(self, db: Session, event: TimelineEvent) -> None:
        db.add(event)

    def list_by_customer(self, db: Session, customer_id: int) -> list[TimelineEvent]:
        return list(db.scalars(select(TimelineEvent).where(TimelineEvent.customer_id == customer_id).order_by(TimelineEvent.occurred_at.desc(), TimelineEvent.id.desc())).all())
