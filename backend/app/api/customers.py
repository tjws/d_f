from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.customer import CustomerCreate, CustomerListResponse, CustomerRead, CustomerStage, CustomerUpdate
from app.services.customer_service import (
    create_customer as create_customer_service,
    customer_scope_filters,
    delete_customer as delete_customer_service,
    get_customer_or_404,
    list_customers as list_customers_service,
    update_customer as update_customer_service,
)

router = APIRouter(prefix="/customers", tags=["customers"])


def _customer_scope_filters(db: Session, current_user: User, action: str):
    """兼容现有模块引用；权限判断实际由 Service 负责。"""
    return customer_scope_filters(db, current_user, action)


def _get_customer_or_404(db: Session, customer_id: int, current_user: User, action: str):
    """兼容现有模块引用；避免其他功能绕过客户数据范围。"""
    return get_customer_or_404(db, customer_id, current_user, action)


@router.post("", response_model=CustomerRead, status_code=status.HTTP_201_CREATED)
def create_customer(payload: CustomerCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return create_customer_service(db, current_user, payload)


@router.get("", response_model=CustomerListResponse)
def list_customers(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), keyword: str | None = Query(default=None, max_length=50), stage: CustomerStage | None = Query(default=None), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    items, total = list_customers_service(db, current_user, page, page_size, keyword, stage)
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get("/{customer_id}", response_model=CustomerRead)
def get_customer(customer_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return get_customer_or_404(db, customer_id, current_user, "read")


@router.patch("/{customer_id}", response_model=CustomerRead)
def update_customer(customer_id: int, payload: CustomerUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return update_customer_service(db, customer_id, current_user, payload)


@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_customer(customer_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    delete_customer_service(db, customer_id, current_user)
