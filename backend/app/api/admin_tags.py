from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.dependencies import require_roles
from app.db.session import get_db
from app.models.user import User
from app.schemas.admin_tag import AdminTagCreate, AdminTagRead, AdminTagUpdate
from app.services.admin_tag_service import create_admin_tag, list_admin_tags, update_admin_tag


router = APIRouter(prefix="/admin/tags", tags=["admin-tags"])


@router.get("", response_model=list[AdminTagRead])
def get_admin_tags(current_user: User = Depends(require_roles("admin", "manager")), db: Session = Depends(get_db)):
    del current_user
    return list_admin_tags(db)


@router.post("", response_model=AdminTagRead, status_code=status.HTTP_201_CREATED)
def post_admin_tag(payload: AdminTagCreate, current_user: User = Depends(require_roles("admin")), db: Session = Depends(get_db)):
    return create_admin_tag(db, current_user, payload)


@router.patch("/{tag_id}", response_model=AdminTagRead)
def patch_admin_tag(tag_id: int, payload: AdminTagUpdate, current_user: User = Depends(require_roles("admin")), db: Session = Depends(get_db)):
    return update_admin_tag(db, current_user, tag_id, payload)
