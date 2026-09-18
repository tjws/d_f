from datetime import datetime
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.core.dependencies import require_roles
from app.db.session import get_db
from app.models.user import User
from app.schemas.ai_dashboard import AIDashboardRead
from app.services.ai_dashboard_service import get_ai_dashboard

router = APIRouter(prefix="/admin/ai-dashboard", tags=["ai-dashboard"])


@router.get("", response_model=AIDashboardRead)
def read_ai_dashboard(
    start: datetime | None = Query(default=None),
    end: datetime | None = Query(default=None),
    current_user: User = Depends(require_roles("admin", "manager")),
    db: Session = Depends(get_db),
):
    return get_ai_dashboard(db, start, end)
