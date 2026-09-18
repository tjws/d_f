import secrets

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password, verify_password
from app.dao.user_dao import UserDAO
from app.models.user import User
from app.schemas.auth import UserCreate


user_dao = UserDAO()


def register_user(db: Session, payload: UserCreate) -> User:
    if user_dao.get_by_username(db, payload.username) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="用户名已存在")
    user = User(username=payload.username, full_name=payload.full_name, hashed_password=hash_password(payload.password))
    user_dao.add(db, user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="用户名已存在") from None
    db.refresh(user)
    return user


def issue_local_token(db: Session, username: str, password: str) -> dict:
    user = user_dao.get_by_username(db, username)
    if user is None or not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误", headers={"WWW-Authenticate": "Bearer"})
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="用户已被停用")
    return {"access_token": create_access_token(subject=user.username), "token_type": "bearer", "role": user.role}


def issue_wecom_token(db: Session, userid: str, username: str, full_name: str) -> dict:
    user = user_dao.get_by_wecom_userid(db, userid)
    if user is None:
        if user_dao.get_by_username(db, username) is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="本地用户名已被其他账号占用")
        user = User(username=username, full_name=full_name, wecom_userid=userid, hashed_password=hash_password(secrets.token_urlsafe(32)))
        user_dao.add(db, user)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="企业微信用户绑定发生冲突") from None
        db.refresh(user)
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="本地用户已被停用")
    return {"access_token": create_access_token(subject=user.username), "token_type": "bearer", "role": user.role}
