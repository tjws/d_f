from fastapi import APIRouter, Depends

from app.core.dependencies import require_roles
from app.models.user import User
from app.schemas.system_status import SystemStatusRead
from app.services.system_status_service import get_system_status


router = APIRouter(prefix="/admin/system-status", tags=["system-status"])


@router.get("", response_model=SystemStatusRead)
def read_system_status(current_user: User = Depends(require_roles("admin", "manager"))):
    """仅管理员和经理可查看；只读检查，不调用百炼。"""
    return get_system_status()
