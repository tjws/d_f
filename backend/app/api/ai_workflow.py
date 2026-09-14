from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.ai_workflow import AIWorkflowRunRead
from app.services.ai_workflow_service import run_customer_ai_workflow


router = APIRouter(
    prefix="/customers/{customer_id}/ai-workflow",
    tags=["ai-workflow"],
)


@router.post("", response_model=AIWorkflowRunRead)
def run_ai_workflow(
    customer_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return run_customer_ai_workflow(db, customer_id, current_user)
