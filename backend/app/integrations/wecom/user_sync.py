import secrets

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.dao.user_dao import UserDAO
from app.models.user import User
from app.schemas.wecom import WeComMockCallback


def sync_mock_user(db: Session, payload: WeComMockCallback) -> User:
    """按企业微信 userid 创建或更新本地用户。"""

    if not payload.username:
        raise ValueError("user_auth 回调缺少 username")

    user_dao = UserDAO()
    user = user_dao.get_by_wecom_userid(db, payload.userid)

    if user is None:
        username_exists = user_dao.get_by_username(db, payload.username)
        if username_exists is not None:
            raise ValueError("本地用户名已被其他账号占用")

        user = User(
            username=payload.username,
            full_name=payload.name,
            wecom_userid=payload.userid,
            role="sales",
            organization_id=None,
            hashed_password=hash_password(secrets.token_urlsafe(32)),
        )
        user_dao.add(db, user)
    elif payload.name:
        user.full_name = payload.name

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ValueError("企业微信用户同步发生冲突") from exc

    db.refresh(user)
    return user
