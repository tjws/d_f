from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.ai_suggestion import AISuggestionRead, AISuggestionUpdate
from app.schemas.schedule import ScheduleCompletion, ScheduleRead, ScheduleUpdate
from app.services.schedule_service import change_schedule_status, confirm_schedule_suggestion, edit_schedule_suggestion, generate_schedule_suggestion, list_schedule_suggestions, list_schedules, update_schedule

router = APIRouter(prefix="/customers/{customer_id}", tags=["schedules"])


@router.post("/schedule-suggestions", response_model=AISuggestionRead, status_code=status.HTTP_201_CREATED)
def create_schedule_suggestion(customer_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _read_suggestion(generate_schedule_suggestion(db, customer_id, current_user))


@router.get("/schedule-suggestions", response_model=list[AISuggestionRead])
def get_schedule_suggestions(customer_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return [_read_suggestion(suggestion) for suggestion in list_schedule_suggestions(db, customer_id, current_user)]


@router.patch("/schedule-suggestions/{suggestion_id}", response_model=AISuggestionRead)
def edit_schedule_suggestion_route(customer_id: int, suggestion_id: int, payload: AISuggestionUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _read_suggestion(edit_schedule_suggestion(db, customer_id, suggestion_id, current_user, payload))


@router.post("/schedule-suggestions/{suggestion_id}/confirm", response_model=ScheduleRead)
def confirm_schedule_suggestion_route(customer_id: int, suggestion_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _read_schedule(confirm_schedule_suggestion(db, customer_id, suggestion_id, current_user))


@router.get("/schedules", response_model=list[ScheduleRead])
def get_schedules(customer_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return [_read_schedule(schedule) for schedule in list_schedules(db, customer_id, current_user)]


@router.patch("/schedules/{schedule_id}", response_model=ScheduleRead)
def edit_schedule(customer_id: int, schedule_id: int, payload: ScheduleUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _read_schedule(update_schedule(db, customer_id, schedule_id, current_user, payload))


@router.post("/schedules/{schedule_id}/complete", response_model=ScheduleRead)
def complete_schedule(customer_id: int, schedule_id: int, payload: ScheduleCompletion | None = None, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _read_schedule(change_schedule_status(db, customer_id, schedule_id, current_user, "completed", payload))


@router.post("/schedules/{schedule_id}/cancel", response_model=ScheduleRead)
def cancel_schedule(customer_id: int, schedule_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _read_schedule(change_schedule_status(db, customer_id, schedule_id, current_user, "cancelled"))


def _read_schedule(schedule) -> ScheduleRead:
    return ScheduleRead(id=schedule.id, customer_id=schedule.customer_id, user_id=schedule.user_id, suggestion_id=schedule.suggestion_id, title=schedule.title, description=schedule.description, due_at=schedule.due_at, priority=schedule.priority, source=schedule.source, status=schedule.status, outcome=schedule.outcome, completion_note=schedule.completion_note, completed_at=schedule.completed_at, evidence=schedule.evidence_json, confirmed_by=schedule.confirmed_by, confirmed_at=schedule.confirmed_at, wecom_calendar_id=schedule.wecom_calendar_id, created_at=schedule.created_at, updated_at=schedule.updated_at)


def _read_suggestion(suggestion) -> AISuggestionRead:
    return AISuggestionRead(id=suggestion.id, customer_id=suggestion.customer_id, user_id=suggestion.user_id, profile_id=suggestion.profile_id, suggestion_type=suggestion.suggestion_type, content=suggestion.content_json, edited_content=suggestion.edited_content_json, evidence=suggestion.evidence_json, evidence_level=suggestion.evidence_level, status=suggestion.status, model_name=suggestion.model_name, model_version=suggestion.model_version, prompt_version=suggestion.prompt_version, decided_by=suggestion.decided_by, decided_at=suggestion.decided_at, created_at=suggestion.created_at)
