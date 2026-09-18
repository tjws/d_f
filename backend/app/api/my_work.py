"""当前登录用户的执行工作台接口。"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.my_work import MyWorkBucket, MyWorkRead
from app.services.my_work_service import get_my_work


router = APIRouter(prefix="/my-work", tags=["my-work"])


@router.get("", response_model=MyWorkRead)
def get_my_work_items(
    bucket: MyWorkBucket | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_my_work(db, current_user, bucket, limit)
