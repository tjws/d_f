from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.permissions import require_permission
from app.dao.audit_log_dao import AuditLogDAO
from app.db.session import get_db
from app.models.audit_log import AuditLog
from app.models.user import User
from app.schemas.audit_log import AuditLogListResponse
from app.services.audit_log_service import list_audit_logs

router = APIRouter(prefix="/audit-logs", tags=["audit-logs"])


@router.get("", response_model=AuditLogListResponse)
def get_audit_logs(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), action: str | None = Query(default=None, max_length=100), actor_user_id: int | None = Query(default=None, ge=1), target_type: str | None = Query(default=None, max_length=50), target_id: str | None = Query(default=None, max_length=100), current_user: User = Depends(require_permission("audit_logs", "read")), db: Session = Depends(get_db)):
    filters = []
    if action:
        filters.append(AuditLog.action == action)
    if actor_user_id is not None:
        filters.append(AuditLog.actor_user_id == actor_user_id)
    if target_type:
        filters.append(AuditLog.target_type == target_type)
    if target_id:
        filters.append(AuditLog.target_id == target_id)
    items, total = list_audit_logs(db, page, page_size, filters)
    return {"items": items, "total": total, "page": page, "page_size": page_size}
