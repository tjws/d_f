from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.dao.admin_permission_dao import AdminPermissionDAO
from app.models.role_permission import RolePermission
from app.models.user import User
from app.schemas.admin_permission import AdminPermissionUpdate
from app.services.audit_log_service import append_audit_log


admin_permission_dao = AdminPermissionDAO()


def list_admin_permissions(db: Session, role: str | None = None, module: str | None = None) -> list[RolePermission]:
    return admin_permission_dao.list_all(db, role, module)


def update_admin_permission(
    db: Session,
    actor: User,
    permission_id: int,
    payload: AdminPermissionUpdate,
) -> RolePermission:
    permission = admin_permission_dao.get_by_id(db, permission_id)
    if permission is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="权限配置不存在")

    # admin 必须保留 all 数据范围，避免管理员把自己锁在管理后台外。
    if permission.role == "admin" and payload.data_scope != "all":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="admin 角色的数据范围必须保持 all")

    # customers 的数据查询只理解 own、organization、all；拒绝 team，避免产生隐含的放行或空结果。
    if permission.module == "customers" and payload.data_scope == "team":
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="customers 模块不支持 team 数据范围")

    if permission.data_scope == payload.data_scope:
        return permission

    before = permission.data_scope
    permission.data_scope = payload.data_scope
    append_audit_log(
        db,
        actor,
        "permission.data_scope_changed",
        "role_permission",
        str(permission.id),
        {
            "role": permission.role,
            "module": permission.module,
            "action": permission.action,
            "before": before,
            "after": permission.data_scope,
        },
    )
    # 权限变更和审计日志共用一个事务，任一失败都会一起回滚。
    db.commit()
    db.refresh(permission)
    return permission
