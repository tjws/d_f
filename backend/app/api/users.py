from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from app.db.session import get_db
from app.core.permissions import require_permission
from app.models.user import User
from app.schemas.auth import UserRead, UserRoleUpdate
from app.models.audit_log import AuditLog
from app.models.organization import Organization
from app.schemas.auth import UserOrganizationUpdate

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
        require_permission("users", "read")
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
        require_permission("users", "role_update")
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

    old_role = target_user.role
    new_role = payload.role.value

    # 请求目标角色没有变化时，不产生无意义的审计记录。
    if old_role == new_role:
        return target_user

    target_user.role = new_role

    # 角色变更和审计记录加入同一个数据库事务。
    db.add(
        AuditLog(
            actor_user_id=current_user.id,
            actor_username_snapshot=current_user.username,
            actor_role_snapshot=current_user.role,
            actor_source="api",
            action="user.role_changed",
            target_type="user",
            target_id=str(target_user.id),
            detail_json={
                "before": {"role": old_role},
                "after": {"role": new_role},
            },
            result="success",
        )
    )

    try:
        # 只有这一次提交，保证角色和审计记录一起成功或一起失败。
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise

    db.refresh(target_user)

    return target_user


@router.patch(
    "/{user_id}/organization",
    response_model=UserRead,
)
def update_user_organization(
    user_id: int,
    payload: UserOrganizationUpdate,
    current_user: User = Depends(
        require_permission("users", "organization_assign")
    ),
    db: Session = Depends(get_db),
):
    """管理员为用户分配或清除组织归属。"""

    target_user = db.get(User, user_id)
    if target_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在",
        )

    if payload.organization_id is not None:
        organization = db.get(Organization, payload.organization_id)
        if organization is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="组织不存在",
            )

    old_organization_id = target_user.organization_id
    new_organization_id = payload.organization_id

    if old_organization_id == new_organization_id:
        return target_user

    target_user.organization_id = new_organization_id
    db.add(
        AuditLog(
            actor_user_id=current_user.id,
            actor_username_snapshot=current_user.username,
            actor_role_snapshot=current_user.role,
            actor_source="api",
            action="user.organization_changed",
            target_type="user",
            target_id=str(target_user.id),
            detail_json={
                "before": {"organization_id": old_organization_id},
                "after": {"organization_id": new_organization_id},
            },
            result="success",
        )
    )

    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise

    db.refresh(target_user)
    return target_user
