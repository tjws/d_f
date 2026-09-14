from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


class AuditLogDAO:
    """审计日志只允许追加写入，DAO 不提供更新或删除方法。"""

    def add(self, db: Session, audit_log: AuditLog) -> None:
        db.add(audit_log)

    def list_page(self, db: Session, filters: list, page: int, page_size: int) -> tuple[list[AuditLog], int]:
        count_statement = select(func.count(AuditLog.id))
        data_statement = select(AuditLog).order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        if filters:
            count_statement = count_statement.where(*filters)
            data_statement = data_statement.where(*filters)
        total = db.scalar(count_statement) or 0
        items = list(db.scalars(data_statement.offset((page - 1) * page_size).limit(page_size)).all())
        return items, total
