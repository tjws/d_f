from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dependencies import require_roles
from app.db.session import get_db
from app.models.user import User
from app.schemas.admin_operations import AdminOperationsRead
from app.schemas.admin_operations_sync import AdminOperationsSyncRead, AdminOperationsSyncRequest
from app.services.admin_operations_service import get_admin_operations
from app.services.admin_operations_sync_service import sync_mock_operations


router = APIRouter(prefix="/admin/operations", tags=["admin-operations"])


@router.get("", response_model=AdminOperationsRead)
def read_admin_operations(
    order_status: str | None = Query(default=None),
    ticket_status: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    current_user: User = Depends(require_roles("admin", "manager")),
    db: Session = Depends(get_db),
):
    return get_admin_operations(db, current_user, order_status, ticket_status, limit)


@router.post("/mock-sync", response_model=AdminOperationsSyncRead)
def mock_sync_operations(payload: AdminOperationsSyncRequest, current_user: User = Depends(require_roles("admin", "manager")), db: Session = Depends(get_db)):
    return sync_mock_operations(db, current_user, payload)
