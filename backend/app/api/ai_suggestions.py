from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.ai_suggestion import AISuggestionRead, AISuggestionUpdate
from app.services.ai_suggestion_service import accept_suggestion, edit_suggestion, generate_reply_draft, list_suggestions, reject_suggestion

router = APIRouter(prefix="/customers/{customer_id}/suggestions", tags=["ai-suggestions"])


def _read(suggestion) -> AISuggestionRead:
    return AISuggestionRead(id=suggestion.id, customer_id=suggestion.customer_id, user_id=suggestion.user_id, profile_id=suggestion.profile_id, suggestion_type=suggestion.suggestion_type, content=suggestion.content_json, edited_content=suggestion.edited_content_json, evidence=suggestion.evidence_json, evidence_level=suggestion.evidence_level, status=suggestion.status, model_name=suggestion.model_name, model_version=suggestion.model_version, prompt_version=suggestion.prompt_version, decided_by=suggestion.decided_by, decided_at=suggestion.decided_at, created_at=suggestion.created_at)


@router.post("/reply-draft", response_model=AISuggestionRead, status_code=status.HTTP_201_CREATED)
def create_reply_draft(customer_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _read(generate_reply_draft(db, customer_id, current_user))


@router.get("", response_model=list[AISuggestionRead])
def get_suggestions(customer_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return [_read(suggestion) for suggestion in list_suggestions(db, customer_id, current_user)]


@router.patch("/{suggestion_id}", response_model=AISuggestionRead)
def edit_reply_suggestion(customer_id: int, suggestion_id: int, payload: AISuggestionUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _read(edit_suggestion(db, customer_id, suggestion_id, current_user, payload))


@router.post("/{suggestion_id}/accept", response_model=AISuggestionRead)
def accept_reply_suggestion(customer_id: int, suggestion_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _read(accept_suggestion(db, customer_id, suggestion_id, current_user))


@router.post("/{suggestion_id}/reject", response_model=AISuggestionRead)
def reject_reply_suggestion(customer_id: int, suggestion_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _read(reject_suggestion(db, customer_id, suggestion_id, current_user))
