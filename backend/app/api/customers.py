from fastapi import APIRouter, status

from app.schemas.customer import CustomerCreate


from fastapi import APIRouter, HTTPException, status

from app.schemas.customer import CustomerCreate, CustomerUpdate


# 客户接口统一使用 /customers 前缀。
router = APIRouter(
    prefix="/customers",
    tags=["customers"],
)


# 临时内存数据，接入数据库后会替换。
_fake_customers: list[dict] = []


def _find_customer(customer_id: int) -> dict:
    """根据 ID 查找客户，找不到时返回 404。"""

    for customer in _fake_customers:
        if customer["id"] == customer_id:
            return customer

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="客户不存在",
    )


@router.post("", status_code=status.HTTP_201_CREATED)
def create_customer(payload: CustomerCreate):
    """创建客户。"""

    customer = {
        "id": len(_fake_customers) + 1,
        **payload.model_dump(),
    }

    _fake_customers.append(customer)
    return customer


@router.get("")
def list_customers():
    """查询全部客户。"""

    return _fake_customers


@router.get("/{customer_id}")
def get_customer(customer_id: int):
    """根据 ID 查询单个客户。"""

    return _find_customer(customer_id)


@router.patch("/{customer_id}")
def update_customer(customer_id: int, payload: CustomerUpdate):
    """只修改请求中提供的字段。"""

    customer = _find_customer(customer_id)

    # exclude_unset=True 可以避免未传入的字段覆盖原数据。
    update_data = payload.model_dump(exclude_unset=True)
    customer.update(update_data)

    return customer


@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_customer(customer_id: int):
    """删除指定客户。"""

    customer = _find_customer(customer_id)
    _fake_customers.remove(customer)