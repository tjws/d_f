from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.dao.organization_dao import OrganizationDAO
from app.dao.user_dao import UserDAO
from app.models.user import User
from app.services.audit_log_service import append_audit_log


user_dao = UserDAO()
organization_dao = OrganizationDAO()


def list_users(db: Session) -> list[User]:
    return user_dao.list_all(db)


def update_user_role(db: Session, current_user: User, user_id: int, new_role: str) -> User:
    target_user = user_dao.get_by_id(db, user_id)
    if target_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    if target_user.id == current_user.id and new_role != "admin":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不能降低自己的管理员权限")
    if target_user.role == "admin" and new_role != "admin" and user_dao.count_active_admins(db) <= 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="系统至少需要保留一个管理员")
    if target_user.role == new_role:
        return target_user
    old_role = target_user.role
    target_user.role = new_role
    append_audit_log(db, current_user, "user.role_changed", "user", str(target_user.id), {"before": {"role": old_role}, "after": {"role": new_role}})
    # 角色变更和审计记录使用同一个 Session，只提交一次。
    db.commit()
    db.refresh(target_user)
    return target_user


def update_user_organization(db: Session, current_user: User, user_id: int, organization_id: int | None) -> User:
    target_user = user_dao.get_by_id(db, user_id)
    if target_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    if organization_id is not None and organization_dao.get_by_id(db, organization_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="组织不存在")
    if target_user.organization_id == organization_id:
        return target_user
    old_organization_id = target_user.organization_id
    target_user.organization_id = organization_id
    append_audit_log(db, current_user, "user.organization_changed", "user", str(target_user.id), {"before": {"organization_id": old_organization_id}, "after": {"organization_id": organization_id}})
    db.commit()
    db.refresh(target_user)
    return target_user
