from fastapi import HTTPException, status
from sqlalchemy import false, or_, select
from sqlalchemy.orm import Session

from app.core.permissions import get_data_scope
from app.dao.customer_dao import CustomerDAO
from app.models.customer import Customer
from app.models.user import User
from app.schemas.customer import CustomerCreate, CustomerStage, CustomerUpdate


customer_dao = CustomerDAO()


def customer_scope_filters(db: Session, current_user: User, action: str) -> list:
    """把权限配置转换为客户查询条件，避免各路由重复实现数据范围。"""
    data_scope = get_data_scope(db, current_user, "customers", action)
    if data_scope is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="当前用户没有执行此操作的权限")
    if data_scope == "all":
        return []
    if data_scope == "own":
        return [Customer.owner_id == current_user.id]
    if data_scope == "organization":
        if current_user.organization_id is None:
            return [false()]
        user_ids = select(User.id).where(User.organization_id == current_user.organization_id)
        return [Customer.owner_id.in_(user_ids)]
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="客户数据范围配置无效")


def get_customer_or_404(db: Session, customer_id: int, current_user: User, action: str) -> Customer:
    customer = customer_dao.get_by_id(db, customer_id, *customer_scope_filters(db, current_user, action))
    if customer is None:
        # 对无权访问与不存在统一返回 404，避免泄露客户是否存在。
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="客户不存在")
    return customer


def create_customer(db: Session, current_user: User, payload: CustomerCreate) -> Customer:
    customer = Customer(owner_id=current_user.id, **payload.model_dump(mode="json"))
    customer_dao.add(db, customer)
    db.commit()
    db.refresh(customer)
    return customer


def list_customers(db: Session, current_user: User, page: int, page_size: int, keyword: str | None, stage: CustomerStage | None) -> tuple[list[Customer], int]:
    filters = customer_scope_filters(db, current_user, "read")
    if keyword:
        search_pattern = f"%{keyword.strip()}%"
        filters.append(or_(Customer.name.ilike(search_pattern), Customer.phone.ilike(search_pattern), Customer.student_name.ilike(search_pattern)))
    if stage:
        filters.append(Customer.stage == stage.value)
    return customer_dao.list_page(db, filters, page, page_size)


def update_customer(db: Session, customer_id: int, current_user: User, payload: CustomerUpdate) -> Customer:
    customer = get_customer_or_404(db, customer_id, current_user, "update")
    for field_name, field_value in payload.model_dump(exclude_unset=True, mode="json").items():
        setattr(customer, field_name, field_value)
    db.commit()
    db.refresh(customer)
    return customer


def delete_customer(db: Session, customer_id: int, current_user: User) -> None:
    customer_dao.delete(db, get_customer_or_404(db, customer_id, current_user, "delete"))
    db.commit()
