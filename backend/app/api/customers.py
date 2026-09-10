from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.customer import Customer
from app.schemas.customer import CustomerCreate, CustomerRead, CustomerUpdate


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


@router.get("", response_model=list[CustomerRead])
def list_customers(db: Session = Depends(get_db)):
    """查询全部客户。"""

    statement = select(Customer).order_by(Customer.id)
    return db.scalars(statement).all()


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