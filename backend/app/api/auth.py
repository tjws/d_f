from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.integrations.wecom.config import WeComConfig
from app.integrations.wecom.mock_adapter import MockWeComAdapter
from app.schemas.auth import Token, UserCreate, UserRead
from app.schemas.wecom import WeComMockLogin
from app.services.auth_service import issue_local_token, issue_wecom_token, register_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    return register_user(db, payload)


@router.post("/token", response_model=Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    return issue_local_token(db, form_data.username, form_data.password)


@router.post("/wecom/mock", response_model=Token)
def mock_wecom_login(payload: WeComMockLogin, db: Session = Depends(get_db)):
    if WeComConfig.from_env().mode != "mock":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mock 企业微信登录未启用")
    try:
        identity = MockWeComAdapter().exchange_code_for_user(payload.code)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return issue_wecom_token(db, identity.userid, identity.username, identity.name)
