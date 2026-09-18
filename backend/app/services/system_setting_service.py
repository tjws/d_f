from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.dao.system_setting_dao import SystemSettingDAO
from app.models.system_setting import SystemSetting
from app.models.user import User
from app.schemas.system_setting import SystemSettingUpdate
from app.services.audit_log_service import append_audit_log


setting_dao = SystemSettingDAO()
ALLOWED_SETTINGS = {
    "ai_daily_bailian_request_limit": (0, 1000),
    "knowledge_max_results": (1, 20),
    "default_follow_up_days": (1, 90),
}
ALLOWED_BOOLEAN_SETTINGS = {"comprehensive_agent_enabled"}
ALLOWED_STRING_SETTINGS = {"ai_rollout_mode": {"all", "pilot"}}


def to_setting_read(setting: SystemSetting) -> dict[str, object]:
    return {"id": setting.id, "key": setting.key, "value": setting.value_json, "scope_type": setting.scope_type, "scope_id": setting.scope_id, "description": setting.description, "updated_by": setting.updated_by, "updated_at": setting.updated_at}


def list_settings(db: Session) -> list[SystemSetting]:
    return setting_dao.list_global(db)


def update_setting(db: Session, key: str, actor: User, payload: SystemSettingUpdate) -> SystemSetting:
    if key in ALLOWED_BOOLEAN_SETTINGS:
        if not isinstance(payload.value, bool):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="设置值必须是布尔值")
        bounds = None
    elif key in ALLOWED_STRING_SETTINGS:
        if not isinstance(payload.value, str) or payload.value not in ALLOWED_STRING_SETTINGS[key]:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="灰度模式只能是 all 或 pilot")
        bounds = None
    else:
        bounds = ALLOWED_SETTINGS.get(key)
        if bounds is None:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="不允许修改该系统设置")
        if not isinstance(payload.value, int) or isinstance(payload.value, bool) or not bounds[0] <= payload.value <= bounds[1]:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"设置值必须是 {bounds[0]} 到 {bounds[1]} 的整数")
    setting = setting_dao.get_global(db, key)
    if setting is None:
        setting = SystemSetting(key=key, scope_type="global", scope_id=None, value_json=payload.value, description=payload.description, updated_by=actor.id)
        setting_dao.add(db, setting)
    else:
        setting.value_json = payload.value
        if payload.description is not None:
            setting.description = payload.description
        setting.updated_by = actor.id
    append_audit_log(db, actor, "system_setting.updated", "system_setting", key, {"value": payload.value})
    db.commit()
    db.refresh(setting)
    return setting


def is_comprehensive_agent_enabled(db: Session) -> bool:
    """读取综合 Agent 开关；缺少迁移时默认开启以保持向后兼容。"""

    return setting_dao.get_global_bool(db, "comprehensive_agent_enabled", True)
