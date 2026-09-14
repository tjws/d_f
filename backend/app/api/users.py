from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.permissions import require_permission
from app.db.session import get_db
from app.schemas.auth import UserOrganizationUpdate, UserRead, UserRoleUpdate
from app.services.user_service import (
    list_users as list_users_service,
    update_user_organization as update_user_organization_service,
    update_user_role as update_user_role_service,
)

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserRead])
def get_users(current_user=Depends(require_permission("users", "read")), db: Session = Depends(get_db)):
    return list_users_service(db)


@router.patch("/{user_id}/role", response_model=UserRead)
def change_user_role(user_id: int, payload: UserRoleUpdate, current_user=Depends(require_permission("users", "role_update")), db: Session = Depends(get_db)):
    """HTTP 层只接收请求；角色保护、审计和事务在 Service 内完成。"""
    return update_user_role_service(db, current_user, user_id, payload.role.value)


@router.patch("/{user_id}/organization", response_model=UserRead)
def change_user_organization(user_id: int, payload: UserOrganizationUpdate, current_user=Depends(require_permission("users", "organization_assign")), db: Session = Depends(get_db)):
    return update_user_organization_service(db, current_user, user_id, payload.organization_id)


# 保留旧函数名，避免维护脚本或现有测试因导入名变化而失效。
update_user_role = change_user_role
update_user_organization = change_user_organization
