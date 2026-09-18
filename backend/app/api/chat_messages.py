from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.integrations.wecom.config import WeComConfig
from app.models.user import User
from app.schemas.chat_message import ChatMessageCreate, ChatMessageRead
from app.services.chat_message_service import ChatMessageConflict, create_chat_message, list_chat_messages, to_chat_message_read
from app.services.customer_service import get_customer_or_404
from app.services.voice_transcription_service import transcribe_voice_message

router = APIRouter(prefix="/customers/{customer_id}/chat-messages", tags=["chat-messages"])


@router.post("/mock", response_model=ChatMessageRead, status_code=status.HTTP_201_CREATED)
def create_mock_chat_message(customer_id: int, payload: ChatMessageCreate, response: Response, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if WeComConfig.from_env().mode != "mock":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mock 聊天消息入口未启用")
    get_customer_or_404(db, customer_id, current_user, "update")
    try:
        message, created = create_chat_message(db, customer_id, current_user, payload)
    except ChatMessageConflict as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if not created:
        response.status_code = status.HTTP_200_OK
    return to_chat_message_read(message)


@router.get("", response_model=list[ChatMessageRead])
def get_chat_messages(customer_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    get_customer_or_404(db, customer_id, current_user, "read")
    return [to_chat_message_read(message) for message in list_chat_messages(db, customer_id)]


@router.post("/{message_id}/transcribe", response_model=ChatMessageRead)
def transcribe_chat_message(customer_id: int, message_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return to_chat_message_read(transcribe_voice_message(db, customer_id, message_id, current_user))
