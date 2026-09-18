from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dependencies import require_roles
from app.db.session import get_db
from app.models.user import User
from app.schemas.admin_permission import AdminPermissionRead, AdminPermissionUpdate
from app.services.admin_permission_service import list_admin_permissions, update_admin_permission


router = APIRouter(prefix="/admin/permissions", tags=["admin-permissions"])


@router.get("", response_model=list[AdminPermissionRead])
def get_admin_permissions(
    role: str | None = Query(default=None, pattern=r"^(admin|manager|sales)$"),
    module: str | None = Query(default=None, min_length=1, max_length=50),
    current_user: User = Depends(require_roles("admin", "manager")),
    db: Session = Depends(get_db),
):
    del current_user
    return list_admin_permissions(db, role, module)


@router.patch("/{permission_id}", response_model=AdminPermissionRead)
def patch_admin_permission(
    permission_id: int,
    payload: AdminPermissionUpdate,
    current_user: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    return update_admin_permission(db, current_user, permission_id, payload)
