"""当前用户的 AI 待处理工作台接口。"""

from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.pending_action import (
    PendingActionDecision,
    PendingActionDecisionRead,
    PendingActionDismissRead,
    PendingActionListRead,
    PendingActionType,
)
from app.services.pending_action_service import list_pending_actions
from app.services.pending_action_service import dismiss_historical_reply, dismiss_reply, review_pending_action


router = APIRouter(prefix="/pending-actions", tags=["pending-actions"])


@router.post("/reply/{resource_id}/dismiss-historical", response_model=PendingActionDismissRead)
def dismiss_historical_reply_action(
    resource_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """仅关闭历史测试草稿；不会删除 AI 建议或审计记录。"""

    return dismiss_historical_reply(db, current_user, resource_id)


@router.post("/reply/{resource_id}/dismiss", response_model=PendingActionDismissRead)
def dismiss_reply_action(
    resource_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """销售主动关闭不再需要的回复建议；不会发送或删除数据。"""

    return dismiss_reply(db, current_user, resource_id)


@router.get("", response_model=PendingActionListRead)
def get_pending_actions(
    action_type: PendingActionType | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """返回当前用户有权处理的 AI 草稿；不执行确认、编辑或发送。"""

    items = list_pending_actions(db, current_user, action_type, limit)
    return {"items": items, "total": len(items)}


@router.post("/{action_type}/{resource_id}/decision", response_model=PendingActionDecisionRead)
def decide_pending_action(
    action_type: PendingActionType,
    resource_id: int,
    payload: PendingActionDecision,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return review_pending_action(db, current_user, action_type, resource_id, payload)
