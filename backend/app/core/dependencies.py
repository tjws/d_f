import jwt
from fastapi import Depends, HTTPException, status
from jwt.exceptions import InvalidTokenError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import ALGORITHM, SECRET_KEY, oauth2_scheme
from app.db.session import get_db
from app.models.user import User


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """解析 JWT，并查询当前登录用户。"""

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无效的登录凭证",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # 验证签名和过期时间。
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
        )
        username = payload.get("sub")

        if not username:
            raise credentials_exception

    except InvalidTokenError:
        raise credentials_exception

    user = db.scalar(
        select(User).where(User.username == username)
    )

    if user is None or not user.is_active:
        raise credentials_exception

    return user