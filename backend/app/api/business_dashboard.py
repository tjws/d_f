from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dependencies import require_roles
from app.db.session import get_db
from app.models.user import User
from app.schemas.business_dashboard import BusinessDashboardRead
from app.services.business_dashboard_service import get_business_dashboard


router = APIRouter(prefix="/admin/business-dashboard", tags=["business-dashboard"])


@router.get("", response_model=BusinessDashboardRead)
def read_business_dashboard(
    start: datetime | None = Query(default=None),
    end: datetime | None = Query(default=None),
    current_user: User = Depends(require_roles("admin", "manager")),
    db: Session = Depends(get_db),
):
    del current_user
    return get_business_dashboard(db, start, end)
