from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.customer import Customer
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


def _get_customer_or_404(db: Session, customer_id: int) -> Customer:
    """根据 ID 查询客户，找不到时返回 404。"""

    customer = db.get(Customer, customer_id)

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
    db: Session = Depends(get_db),
):
    """创建客户并保存到数据库。"""

    # mode="json" 会把枚举转换为普通字符串，方便写入数据库。
    customer = Customer(**payload.model_dump(mode="json"))

    db.add(customer)
    db.commit()
    db.refresh(customer)

    return customer


@router.get("", response_model=CustomerListResponse)
def list_customers(
    page: int = Query(1, ge=1, description="页码，从 1 开始"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    keyword: str | None = Query(
        default=None,
        max_length=50,
        description="搜索家长姓名、手机号或学生姓名",
    ),
    stage: CustomerStage | None = Query(
        default=None,
        description="按意向阶段筛选",
    ),
    db: Session = Depends(get_db),
):
    """分页查询客户，并支持关键词和意向阶段筛选。"""

    filters = []

    if keyword:
        keyword = keyword.strip()
        search_pattern = f"%{keyword}%"

        filters.append(
            or_(
                Customer.name.ilike(search_pattern),
                Customer.phone.ilike(search_pattern),
                Customer.student_name.ilike(search_pattern),
            )
        )

    if stage:
        filters.append(Customer.stage == stage.value)

    # 先统计符合条件的客户总数。
    count_statement = select(func.count(Customer.id))

    # 再查询当前页的数据。
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
    db: Session = Depends(get_db),
):
    """根据 ID 查询单个客户。"""

    return _get_customer_or_404(db, customer_id)


@router.patch("/{customer_id}", response_model=CustomerRead)
def update_customer(
    customer_id: int,
    payload: CustomerUpdate,
    db: Session = Depends(get_db),
):
    """只修改请求中提供的字段。"""

    customer = _get_customer_or_404(db, customer_id)

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
    db: Session = Depends(get_db),
):
    """删除指定客户。"""

    customer = _get_customer_or_404(db, customer_id)

    db.delete(customer)
    db.commit()