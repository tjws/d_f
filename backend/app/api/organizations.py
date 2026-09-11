from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.core.permissions import require_permission
from app.db.session import get_db
from app.models.audit_log import AuditLog
from app.models.organization import Organization
from app.schemas.organization import OrganizationCreate, OrganizationRead


router = APIRouter(
    prefix="/organizations",
    tags=["organizations"],
)


@router.get("", response_model=list[OrganizationRead])
def list_organizations(
    current_user=Depends(
        require_permission("organizations", "read")
    ),
    db: Session = Depends(get_db),
):
    """管理员查看组织节点列表，前端可依据 parent_id 组装树。"""

    return db.scalars(
        select(Organization).order_by(Organization.id)
    ).all()


@router.post(
    "",
    response_model=OrganizationRead,
    status_code=status.HTTP_201_CREATED,
)
def create_organization(
    payload: OrganizationCreate,
    current_user=Depends(
        require_permission("organizations", "create")
    ),
    db: Session = Depends(get_db),
):
    """管理员创建组织节点。"""

    parent = None
    if payload.parent_id is not None:
        parent = db.get(Organization, payload.parent_id)
        if parent is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="父组织不存在",
            )

    organization = Organization(
        name=payload.name,
        type=payload.type,
        parent_id=payload.parent_id,
    )
    db.add(organization)
    db.flush()

    # 用节点 id 生成稳定路径，便于后续查询下属组织。
    parent_path = (
        parent.path
        if parent is not None and parent.path
        else f"/{parent.id}"
        if parent is not None
        else ""
    )
    organization.path = (
        f"{parent_path}/{organization.id}"
        if parent_path
        else f"/{organization.id}"
    )

    db.add(
        AuditLog(
            actor_user_id=current_user.id,
            actor_username_snapshot=current_user.username,
            actor_role_snapshot=current_user.role,
            actor_source="api",
            action="organization.created",
            target_type="organization",
            target_id=str(organization.id),
            detail_json={
                "name": organization.name,
                "type": organization.type,
                "parent_id": organization.parent_id,
            },
            result="success",
        )
    )

    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise

    db.refresh(organization)
    return organization
