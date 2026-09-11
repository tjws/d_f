from collections.abc import Callable

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.role_permission import RolePermission
from app.models.user import User


def get_data_scope(
    db: Session,
    user: User,
    module: str,
    action: str,
) -> str | None:
    """查询用户对指定模块和操作的数据范围。"""

    statement = select(RolePermission.data_scope).where(
        RolePermission.role == user.role,
        RolePermission.module == module,
        RolePermission.action == action,
    )

    return db.scalar(statement)


def has_permission(
    db: Session,
    user: User,
    module: str,
    action: str,
) -> bool:
    """判断用户是否拥有指定操作权限。"""

    return get_data_scope(
        db,
        user,
        module,
        action,
    ) is not None


def require_permission(
    module: str,
    action: str,
) -> Callable:
    """创建基于权限表的 FastAPI 鉴权依赖。"""

    def permission_checker(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> User:
        """进入接口前检查角色是否拥有指定操作权限。"""

        if not has_permission(
            db,
            current_user,
            module,
            action,
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="当前用户没有执行此操作的权限",
            )

        return current_user

    return permission_checker
