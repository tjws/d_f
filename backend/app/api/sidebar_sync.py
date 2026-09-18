from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.sidebar_sync import SidebarSyncRead
from app.services.sidebar_sync_service import get_sidebar_sync


router = APIRouter(prefix="/customers/{customer_id}/sidebar-sync", tags=["sidebar-sync"])


@router.get("", response_model=SidebarSyncRead)
def read_sidebar_sync(
    customer_id: int,
    after_message_id: int = Query(default=0, ge=0),
    after_timeline_id: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """给本地 Mock 侧边栏提供轻量增量同步，不绕过客户权限。"""

    return get_sidebar_sync(db, customer_id, current_user, after_message_id, after_timeline_id)
