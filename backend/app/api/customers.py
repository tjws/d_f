from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

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


def _can_view_all_customers(user: User) -> bool:
    """判断用户是否可以查看全部客户。"""

    return user.role in {"admin", "manager"}


def _get_customer_or_404(
    db: Session,
    customer_id: int,
    current_user: User,
) -> Customer:
    """查询客户，并检查当前用户是否有权访问。"""

    customer = db.get(Customer, customer_id)

    if customer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="客户不存在",
        )

    # 对无权限用户也返回 404，避免泄露客户是否存在。
    if (
        not _can_view_all_customers(current_user)
        and customer.owner_id != current_user.id
    ):
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

    # 销售只能看到自己的客户。
    if not _can_view_all_customers(current_user):
        filters.append(Customer.owner_id == current_user.id)

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
    )

    db.delete(customer)
    db.commit()