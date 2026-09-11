from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import false, func, or_, select
from sqlalchemy.orm import Session
from app.core.permissions import get_data_scope
from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.customer import Customer
from app.models.user import User
from app.schemas.customer import (
    CustomerCreate,
    CustomerListResponse,
    CustomerRead,
    CustomerStage,
    CustomerUpdate,
)


router = APIRouter(
    prefix="/customers",
    tags=["customers"],
)


def _customer_scope_filters(
    db: Session,
    current_user: User,
    action: str,
):
    """根据权限表生成客户查询范围。"""

    data_scope = get_data_scope(
        db,
        current_user,
        "customers",
        action,
    )

    if data_scope is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="当前用户没有执行此操作的权限",
        )

    if data_scope == "all":
        return []

    if data_scope == "own":
        return [Customer.owner_id == current_user.id]

    if data_scope == "organization":
        # 未分配组织的经理不能看到组织范围客户。
        if current_user.organization_id is None:
            return [false()]

        organization_user_ids = select(User.id).where(
            User.organization_id == current_user.organization_id
        )

        return [
            Customer.owner_id.in_(organization_user_ids)
        ]

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="客户数据范围配置无效",
    )


def _get_customer_or_404(
    db: Session,
    customer_id: int,
    current_user: User,
    action: str,
) -> Customer:
    """查询客户，并检查当前用户的数据范围。"""

    filters = _customer_scope_filters(
        db,
        current_user,
        action,
    )

    customer = db.scalar(
        select(Customer).where(
            Customer.id == customer_id,
            *filters,
        )
    )

    if customer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="客户不存在",
        )

    return customer


@router.post(
    "",
    response_model=CustomerRead,
    status_code=status.HTTP_201_CREATED,
)
def create_customer(
    payload: CustomerCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """创建客户，并自动将当前用户设为负责人。"""

    customer = Customer(
        owner_id=current_user.id,
        **payload.model_dump(mode="json"),
    )

    db.add(customer)
    db.commit()
    db.refresh(customer)

    return customer


@router.get("", response_model=CustomerListResponse)
def list_customers(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str | None = Query(default=None, max_length=50),
    stage: CustomerStage | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """分页查询客户，并根据角色限制数据范围。"""

    filters = []

    filters.extend(
        _customer_scope_filters(
            db,
            current_user,
            "read",
        )
    )

    if keyword:
        search_pattern = f"%{keyword.strip()}%"

        filters.append(
            or_(
                Customer.name.ilike(search_pattern),
                Customer.phone.ilike(search_pattern),
                Customer.student_name.ilike(search_pattern),
            )
        )

    if stage:
        filters.append(Customer.stage == stage.value)

    count_statement = select(func.count(Customer.id))
    data_statement = select(Customer).order_by(Customer.id)

    if filters:
        count_statement = count_statement.where(*filters)
        data_statement = data_statement.where(*filters)

    total = db.scalar(count_statement) or 0

    data_statement = data_statement.offset(
        (page - 1) * page_size
    ).limit(page_size)

    items = db.scalars(data_statement).all()

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/{customer_id}", response_model=CustomerRead)
def get_customer(
    customer_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """查询单个客户。"""

    return _get_customer_or_404(
        db,
        customer_id,
        current_user,
        "read",
    )


@router.patch("/{customer_id}", response_model=CustomerRead)
def update_customer(
    customer_id: int,
    payload: CustomerUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """修改当前用户有权限访问的客户。"""

    customer = _get_customer_or_404(
        db,
        customer_id,
        current_user,
        "update",
    )

    update_data = payload.model_dump(
        exclude_unset=True,
        mode="json",
    )

    for field_name, field_value in update_data.items():
        setattr(customer, field_name, field_value)

    db.commit()
    db.refresh(customer)

    return customer


@router.delete(
    "/{customer_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_customer(
    customer_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """删除当前用户有权限访问的客户。"""

    customer = _get_customer_or_404(
        db,
        customer_id,
        current_user,
        "delete",
    )

    db.delete(customer)
    db.commit()