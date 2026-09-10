from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.dependencies import require_roles
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import UserRead, UserRoleUpdate


router = APIRouter(
    prefix="/users",
    tags=["users"],
)


@router.get(
    "",
    response_model=list[UserRead],
)
def list_users(
    current_user: User = Depends(
        require_roles("admin", "manager")
    ),
    db: Session = Depends(get_db),
):
    """管理员和经理可以查看用户列表。"""

    statement = select(User).order_by(User.id)
    return db.scalars(statement).all()


@router.patch(
    "/{user_id}/role",
    response_model=UserRead,
)
def update_user_role(
    user_id: int,
    payload: UserRoleUpdate,
    current_user: User = Depends(
        require_roles("admin")
    ),
    db: Session = Depends(get_db),
):
    """只有管理员可以修改用户角色。"""

    target_user = db.scalar(
        select(User).where(User.id == user_id)
    )

    if target_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在",
        )

    # 防止管理员误操作导致自己失去管理权限。
    if (
        target_user.id == current_user.id
        and payload.role.value != "admin"
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能降低自己的管理员权限",
        )

    # 防止系统出现没有管理员的状态。
    if (
        target_user.role == "admin"
        and payload.role.value != "admin"
    ):
        active_admin_count = db.scalar(
            select(func.count(User.id)).where(
                User.role == "admin",
                User.is_active.is_(True),
            )
        ) or 0

        if active_admin_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="系统至少需要保留一个管理员",
            )

    target_user.role = payload.role.value
    db.commit()
    db.refresh(target_user)

    return target_user
