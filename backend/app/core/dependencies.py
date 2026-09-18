import os
from collections.abc import Callable

import jwt
from fastapi import Depends, HTTPException, status
from jwt.exceptions import InvalidTokenError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import ALGORITHM, SECRET_KEY, oauth2_scheme
from app.db.session import get_db
from app.models.user import User
from app.core.request_context import set_actor_user_id

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

    set_actor_user_id(user.id)
    return user


def get_dev_user(
    db: Session = Depends(get_db),
) -> User:
    """仅供本地开发测试使用的固定用户，不读取请求中的 JWT。"""

    username = os.getenv("APP_DEV_USERNAME", "dev_admin")
    user = db.scalar(
        select(User).where(User.username == username)
    )

    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="开发测试用户不存在或已停用",
        )

    set_actor_user_id(user.id)
    return user

def require_roles(*allowed_roles: str) -> Callable:
    """创建角色权限检查器。"""

    def role_checker(
        current_user: User = Depends(get_current_user),
    ) -> User:
        """确认当前用户拥有允许的角色。"""

        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="当前用户没有执行此操作的权限",
            )

        return current_user

    return role_checker
