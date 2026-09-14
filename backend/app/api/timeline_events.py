from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.timeline_event import TimelineEventCreate, TimelineEventRead
from app.services.timeline_event_service import create_timeline_event as create_timeline_event_service, list_timeline_events as list_timeline_events_service, to_timeline_event_read

router = APIRouter(prefix="/customers/{customer_id}/timeline-events", tags=["timeline-events"])


@router.post("", response_model=TimelineEventRead, status_code=status.HTTP_201_CREATED)
def create_timeline_event(customer_id: int, payload: TimelineEventCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return to_timeline_event_read(create_timeline_event_service(db, customer_id, current_user, payload))


@router.get("", response_model=list[TimelineEventRead])
def list_timeline_events(customer_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return [to_timeline_event_read(event) for event in list_timeline_events_service(db, customer_id, current_user)]
