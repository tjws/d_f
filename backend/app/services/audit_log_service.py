from app.dao.audit_log_dao import AuditLogDAO
from app.models.audit_log import AuditLog
from app.models.user import User
from sqlalchemy.orm import Session
from app.core.request_context import request_id_var


audit_log_dao = AuditLogDAO()


def append_audit_log(db: Session, actor: User, action: str, target_type: str, target_id: str, detail_json: dict | None = None, actor_source: str = "api") -> AuditLog:
    """创建待提交的审计记录；调用者必须与业务修改共用同一个事务。"""
    log = AuditLog(
        actor_user_id=actor.id,
        actor_username_snapshot=actor.username,
        actor_role_snapshot=actor.role,
        actor_source=actor_source,
        action=action,
        target_type=target_type,
        target_id=target_id,
        detail_json=detail_json,
        result="success",
        request_id=request_id_var.get() or None,
    )
    audit_log_dao.add(db, log)
    return log


def append_system_audit_log(db: Session, actor_source: str, action: str, target_type: str, target_id: str, result: str, detail_json: dict | None = None) -> AuditLog:
    """用于没有内部登录用户的回调审计，不写入签名、密钥或完整敏感明文。"""
    log = AuditLog(actor_user_id=None, actor_username_snapshot=None, actor_role_snapshot=None, actor_source=actor_source, action=action, target_type=target_type, target_id=target_id, detail_json=detail_json, result=result, request_id=request_id_var.get() or None)
    audit_log_dao.add(db, log)
    return log


def list_audit_logs(db: Session, page: int, page_size: int, filters: list) -> tuple[list[AuditLog], int]:
    return audit_log_dao.list_page(db, filters, page, page_size)
