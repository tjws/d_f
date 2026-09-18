from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.dao.ai_suggestion_dao import AISuggestionDAO
from app.models.user import User
from app.schemas.ai_suggestion import AISuggestionRead, AISuggestionUpdate
from app.services.ai_suggestion_service import accept_suggestion, edit_suggestion, generate_reply_draft, list_suggestions, reject_suggestion
from app.services.ai_suggestion_feedback_service import feedback_dao
from app.schemas.ai_suggestion_feedback import AISuggestionFeedbackRead

router = APIRouter(prefix="/customers/{customer_id}/suggestions", tags=["ai-suggestions"])
suggestion_dao = AISuggestionDAO()


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


@router.get("/{suggestion_id}/feedback", response_model=AISuggestionFeedbackRead)
def get_suggestion_feedback(customer_id: int, suggestion_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # 先通过建议列表查询校验客户归属和数据权限，再返回反馈。
    suggestion = suggestion_dao.get_by_id(db, customer_id, suggestion_id)
    if suggestion is None:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AI 建议不存在")
    from app.services.customer_service import get_customer_or_404
    get_customer_or_404(db, customer_id, current_user, "read")
    feedback = feedback_dao.get_by_suggestion(db, suggestion_id)
    if feedback is None:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="该建议尚无人工反馈")
    return feedback
