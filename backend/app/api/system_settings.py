from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import require_roles
from app.db.session import get_db
from app.models.user import User
from app.schemas.system_setting import SystemSettingRead, SystemSettingUpdate
from app.services.system_setting_service import list_settings, to_setting_read, update_setting


router = APIRouter(prefix="/admin/system-settings", tags=["system-settings"])


@router.get("", response_model=list[SystemSettingRead])
def get_system_settings(current_user: User = Depends(require_roles("admin", "manager")), db: Session = Depends(get_db)):
    return [to_setting_read(item) for item in list_settings(db)]


@router.put("/{key}", response_model=SystemSettingRead)
def put_system_setting(key: str, payload: SystemSettingUpdate, current_user: User = Depends(require_roles("admin")), db: Session = Depends(get_db)):
    return to_setting_read(update_setting(db, key, current_user, payload))
