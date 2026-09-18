from datetime import date

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import require_roles
from app.db.session import get_db
from app.models.user import User
from app.schemas.ai_rollout import (
    AIRolloutConfigRead,
    AIRolloutMemberCreate,
    AIRolloutMemberRead,
    AIRolloutModeUpdate,
    AIRolloutReportRead,
)
from app.services.ai_rollout_service import (
    add_member,
    config_read,
    generate_daily_report,
    list_members,
    list_reports,
    remove_member,
    set_mode,
)


router = APIRouter(prefix="/admin/ai-rollout", tags=["ai-rollout"])


@router.get("/config", response_model=AIRolloutConfigRead)
def get_rollout_config(current_user: User = Depends(require_roles("admin", "manager")), db: Session = Depends(get_db)):
    del current_user
    return config_read(db)


@router.put("/config", response_model=AIRolloutConfigRead)
def put_rollout_config(payload: AIRolloutModeUpdate, current_user: User = Depends(require_roles("admin")), db: Session = Depends(get_db)):
    return set_mode(db, current_user, payload.mode)


@router.get("/members", response_model=list[AIRolloutMemberRead])
def get_rollout_members(current_user: User = Depends(require_roles("admin", "manager")), db: Session = Depends(get_db)):
    del current_user
    return list_members(db)


@router.post("/members", response_model=AIRolloutMemberRead, status_code=status.HTTP_201_CREATED)
def post_rollout_member(payload: AIRolloutMemberCreate, current_user: User = Depends(require_roles("admin")), db: Session = Depends(get_db)):
    return add_member(db, current_user, payload)


@router.delete("/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_rollout_member(user_id: int, current_user: User = Depends(require_roles("admin")), db: Session = Depends(get_db)):
    remove_member(db, current_user, user_id)


@router.get("/reports", response_model=list[AIRolloutReportRead])
def get_rollout_reports(limit: int = Query(default=30, ge=1, le=90), current_user: User = Depends(require_roles("admin", "manager")), db: Session = Depends(get_db)):
    del current_user
    return list_reports(db, limit)


@router.post("/reports/generate", response_model=AIRolloutReportRead)
def post_rollout_daily_report(report_date: date | None = None, current_user: User = Depends(require_roles("admin")), db: Session = Depends(get_db)):
    return generate_daily_report(db, current_user, report_date)

