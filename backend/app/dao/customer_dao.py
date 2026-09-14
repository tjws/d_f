from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.customer import Customer


class CustomerDAO:
    """客户表的查询和写入操作；提交事务由 Service 负责。"""

    def get_by_id(self, db: Session, customer_id: int, *filters) -> Customer | None:
        return db.scalar(select(Customer).where(Customer.id == customer_id, *filters))

    def list_page(self, db: Session, filters: list, page: int, page_size: int) -> tuple[list[Customer], int]:
        count_statement = select(func.count(Customer.id))
        data_statement = select(Customer).order_by(Customer.id)
        if filters:
            count_statement = count_statement.where(*filters)
            data_statement = data_statement.where(*filters)
        total = db.scalar(count_statement) or 0
        items = list(db.scalars(data_statement.offset((page - 1) * page_size).limit(page_size)).all())
        return items, total

    def add(self, db: Session, customer: Customer) -> None:
        db.add(customer)

    def delete(self, db: Session, customer: Customer) -> None:
        db.delete(customer)
