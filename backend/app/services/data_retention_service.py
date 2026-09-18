from datetime import datetime, timedelta, timezone
import os

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.dao.admin_retention_dao import AdminRetentionDAO
from app.models.user import User
from app.schemas.admin_retention import RetentionPurgeRequest, RetentionPreviewRequest
from app.services.audit_log_service import append_audit_log


DEFAULT_RETENTION_DAYS = {
    "customers": 3650,
    "chat_messages": 730,
    "audit_logs": 3650,
    "ai_feedback": 1095,
}
_DELETABLE = {"chat_messages", "ai_feedback"}
retention_dao = AdminRetentionDAO()


def _env_days(dataset: str) -> int:
    key = f"DATA_RETENTION_{dataset.upper()}_DAYS"
    raw = os.getenv(key, str(DEFAULT_RETENTION_DAYS[dataset])).strip()
    try:
        value = int(raw)
    except ValueError:
        value = DEFAULT_RETENTION_DAYS[dataset]
    return max(1, min(value, 36500))


def deletion_enabled() -> bool:
    return os.getenv("DATA_RETENTION_AUTO_DELETE", "0").strip() == "1"


def get_policy() -> dict[str, object]:
    return {
        "automatic_deletion_enabled": deletion_enabled(),
        "configured_at": "environment",
        "datasets": [
            {
                "dataset": dataset,
                "retention_days": _env_days(dataset),
                "automatic_deletion_allowed": dataset in _DELETABLE,
                "note": "可受控清理" if dataset in _DELETABLE else "只读保留，不允许此工具删除",
            }
            for dataset in DEFAULT_RETENTION_DAYS
        ],
        "non_deletable_datasets": ["customers", "audit_logs"],
        "note": "默认仅预览；自动删除开关默认为关闭，任何清理都需要管理员显式确认并写入审计日志。",
    }


def _before(dataset: str, value: datetime | None) -> datetime:
    if value is not None:
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) - timedelta(days=_env_days(dataset))


def preview(db: Session, payload: RetentionPreviewRequest) -> dict[str, object]:
    before = _before(payload.dataset, payload.before)
    count, oldest, newest = retention_dao.preview(db, payload.dataset, before)
    return {
        "dataset": payload.dataset,
        "before": before,
        "matching_rows": count,
        "oldest_created_at": oldest,
        "newest_created_at": newest,
        "deletion_allowed": deletion_enabled() and payload.dataset in _DELETABLE,
    }


def purge(db: Session, actor: User, payload: RetentionPurgeRequest) -> dict[str, object]:
    if payload.dataset not in _DELETABLE:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="该数据集不允许通过保留工具删除")
    if not deletion_enabled():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="DATA_RETENTION_AUTO_DELETE 未开启，当前只允许预览")
    if not payload.confirm:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="必须提供 confirm=true 才能清理")
    before = _before(payload.dataset, payload.before)
    deleted = retention_dao.delete_before(db, payload.dataset, before)
    log = append_audit_log(
        db,
        actor,
        "admin.data_retention_purged",
        "data_retention",
        payload.dataset,
        {"before": before.isoformat(), "deleted_rows": deleted},
    )
    db.commit()
    return {"dataset": payload.dataset, "before": before, "deleted_rows": deleted, "audit_log_id": log.id}
