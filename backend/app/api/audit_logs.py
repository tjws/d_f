from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.permissions import require_permission
from app.db.session import get_db
from app.models.audit_log import AuditLog
from app.models.user import User
from app.schemas.audit_log import AuditLogListResponse


router = APIRouter(
    prefix="/audit-logs",
    tags=["audit-logs"],
)


@router.get("", response_model=AuditLogListResponse)
def list_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    action: str | None = Query(default=None, max_length=100),
    actor_user_id: int | None = Query(default=None, ge=1),
    target_type: str | None = Query(default=None, max_length=50),
    target_id: str | None = Query(default=None, max_length=100),
    current_user: User = Depends(
        require_permission("audit_logs", "read")
    ),
    db: Session = Depends(get_db),
):
    """管理员分页查询审计日志；本接口不提供修改和删除能力。"""

    filters = []
    if action:
        filters.append(AuditLog.action == action)
    if actor_user_id is not None:
        filters.append(AuditLog.actor_user_id == actor_user_id)
    if target_type:
        filters.append(AuditLog.target_type == target_type)
    if target_id:
        filters.append(AuditLog.target_id == target_id)

    count_statement = select(func.count(AuditLog.id))
    data_statement = select(AuditLog).order_by(
        AuditLog.created_at.desc(),
        AuditLog.id.desc(),
    )

    if filters:
        count_statement = count_statement.where(*filters)
        data_statement = data_statement.where(*filters)

    total = db.scalar(count_statement) or 0
    items = db.scalars(
        data_statement
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }
