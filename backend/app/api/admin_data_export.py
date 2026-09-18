from datetime import datetime

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.core.dependencies import require_roles
from app.db.session import get_db
from app.models.user import User
from app.schemas.admin_data_export import DataExportDataset, DataExportFormat, DataRetentionPolicyRead
from app.services.admin_data_export_service import export_dataset, get_retention_policy


router = APIRouter(prefix="/admin/data-export", tags=["admin-data-export"])


@router.get("/policy", response_model=DataRetentionPolicyRead)
def read_data_retention_policy(current_user: User = Depends(require_roles("admin"))):
    del current_user
    return get_retention_policy()


@router.get("/{dataset}")
def download_data_export(
    dataset: DataExportDataset,
    output_format: DataExportFormat = Query(default="csv", alias="format"),
    start: datetime | None = Query(default=None),
    end: datetime | None = Query(default=None),
    limit: int = Query(default=1000, ge=1, le=10000),
    current_user: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    content, media_type, filename = export_dataset(db, current_user, dataset, output_format, start, end, limit)
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
