from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.role_permission import RolePermission


class AdminPermissionDAO:
    """管理后台权限矩阵的查询和更新入口。"""

    def list_all(self, db: Session, role: str | None = None, module: str | None = None) -> list[RolePermission]:
        statement = select(RolePermission).order_by(RolePermission.role, RolePermission.module, RolePermission.action)
        if role:
            statement = statement.where(RolePermission.role == role)
        if module:
            statement = statement.where(RolePermission.module == module)
        return list(db.scalars(statement).all())

    def get_by_id(self, db: Session, permission_id: int) -> RolePermission | None:
        return db.get(RolePermission, permission_id)
