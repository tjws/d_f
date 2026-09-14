from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.crypto import decrypt_text, encrypt_text
from app.dao.timeline_event_dao import TimelineEventDAO
from app.models.timeline_event import TimelineEvent
from app.models.user import User
from app.schemas.timeline_event import TimelineEventCreate, TimelineEventRead
from app.services.customer_service import get_customer_or_404


timeline_event_dao = TimelineEventDAO()


def to_timeline_event_read(event: TimelineEvent) -> TimelineEventRead:
    return TimelineEventRead(id=event.id, customer_id=event.customer_id, operator_id=event.operator_id, occurred_at=event.occurred_at, event_type=event.event_type, summary=decrypt_text(event.summary_encrypted), source=event.source, reference_type=event.reference_type, reference_id=event.reference_id, created_at=event.created_at)


def create_timeline_event(db: Session, customer_id: int, current_user: User, payload: TimelineEventCreate) -> TimelineEvent:
    get_customer_or_404(db, customer_id, current_user, "update")
    event = TimelineEvent(customer_id=customer_id, operator_id=current_user.id, occurred_at=payload.occurred_at or datetime.now(timezone.utc), event_type=payload.event_type, summary_encrypted=encrypt_text(payload.summary), source="manual", reference_type=payload.reference_type, reference_id=payload.reference_id)
    timeline_event_dao.add(db, event)
    db.commit()
    db.refresh(event)
    return event


def list_timeline_events(db: Session, customer_id: int, current_user: User) -> list[TimelineEvent]:
    get_customer_or_404(db, customer_id, current_user, "read")
    return timeline_event_dao.list_by_customer(db, customer_id)
