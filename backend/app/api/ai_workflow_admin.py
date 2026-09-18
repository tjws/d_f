from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dependencies import require_roles
from app.db.session import get_db
from app.models.user import User
from app.schemas.ai_workflow_admin import (
    AIWorkflowRecoveryRead,
    AIWorkflowRecoveryRequest,
    AIWorkflowRunAdminList,
)
from app.services.ai_workflow_admin_service import list_workflow_runs, recover_stale_workflow_runs


router = APIRouter(prefix="/admin/ai-workflow-runs", tags=["ai-workflow-admin"])


@router.get("", response_model=AIWorkflowRunAdminList)
def get_ai_workflow_runs(
    start: datetime | None = Query(default=None),
    end: datetime | None = Query(default=None),
    provider_name: str | None = Query(default=None, max_length=30),
    status: str | None = Query(default=None, max_length=20),
    limit: int = Query(default=50, ge=1, le=200),
    current_user: User = Depends(require_roles("admin", "manager")),
    db: Session = Depends(get_db),
):
    del current_user
    return list_workflow_runs(db, start, end, provider_name, status, limit)


@router.post("/recover-stale", response_model=AIWorkflowRecoveryRead)
def recover_stale_runs(
    payload: AIWorkflowRecoveryRequest,
    current_user: User = Depends(require_roles("admin", "manager")),
    db: Session = Depends(get_db),
):
    return recover_stale_workflow_runs(
        db,
        current_user,
        payload.confirm,
        payload.stale_after_seconds,
        payload.limit,
    )
