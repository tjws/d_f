from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.dependencies import require_roles
from app.db.session import get_db
from app.models.user import User
from app.schemas.sales_script import SalesScriptCreate, SalesScriptRead, SalesScriptUpdate
from app.services.sales_script_service import create_script, list_scripts, to_script_read, update_script


router = APIRouter(prefix="/admin/sales-scripts", tags=["sales-scripts"])


@router.get("", response_model=list[SalesScriptRead])
def get_sales_scripts(current_user: User = Depends(require_roles("admin", "manager")), db: Session = Depends(get_db)):
    return [to_script_read(item) for item in list_scripts(db)]


@router.post("", response_model=SalesScriptRead, status_code=status.HTTP_201_CREATED)
def post_sales_script(payload: SalesScriptCreate, current_user: User = Depends(require_roles("admin", "manager")), db: Session = Depends(get_db)):
    return to_script_read(create_script(db, current_user, payload))


@router.patch("/{script_id}", response_model=SalesScriptRead)
def patch_sales_script(script_id: int, payload: SalesScriptUpdate, current_user: User = Depends(require_roles("admin", "manager")), db: Session = Depends(get_db)):
    return to_script_read(update_script(db, script_id, current_user, payload))
