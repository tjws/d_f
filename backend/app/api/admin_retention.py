from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import require_roles
from app.db.session import get_db
from app.models.user import User
from app.schemas.admin_retention import (
    RetentionPurgeRead,
    RetentionPurgeRequest,
    RetentionPolicyRead,
    RetentionPreviewRead,
    RetentionPreviewRequest,
)
from app.services.data_retention_service import get_policy, preview, purge


router = APIRouter(prefix="/admin/data-retention", tags=["admin-data-retention"])


@router.get("", response_model=RetentionPolicyRead)
def read_retention_policy(current_user: User = Depends(require_roles("admin"))):
    del current_user
    return get_policy()


@router.post("/preview", response_model=RetentionPreviewRead)
def preview_retention(payload: RetentionPreviewRequest, current_user: User = Depends(require_roles("admin")), db: Session = Depends(get_db)):
    del current_user
    return preview(db, payload)


@router.post("/purge", response_model=RetentionPurgeRead)
def purge_retention(payload: RetentionPurgeRequest, current_user: User = Depends(require_roles("admin")), db: Session = Depends(get_db)):
    return purge(db, current_user, payload)
