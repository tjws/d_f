from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.system_setting import SystemSetting


class SystemSettingDAO:
    def list_global(self, db: Session) -> list[SystemSetting]:
        return list(db.scalars(select(SystemSetting).where(SystemSetting.scope_type == "global").order_by(SystemSetting.key)).all())

    def get_global(self, db: Session, key: str) -> SystemSetting | None:
        return db.scalar(select(SystemSetting).where(SystemSetting.key == key, SystemSetting.scope_type == "global", SystemSetting.scope_id.is_(None)))

    def add(self, db: Session, setting: SystemSetting) -> None:
        db.add(setting)

    def get_global_int(self, db: Session, key: str, default: int) -> int:
        """读取受控整数设置；数据库中的异常值回退到安全默认值。"""
        setting = self.get_global(db, key)
        value = setting.value_json if setting is not None else None
        return value if isinstance(value, int) and not isinstance(value, bool) else default

    def get_global_bool(self, db: Session, key: str, default: bool) -> bool:
        """读取布尔开关；缺失或异常值回退到安全默认值。"""

        setting = self.get_global(db, key)
        value = setting.value_json if setting is not None else None
        return value if isinstance(value, bool) else default
