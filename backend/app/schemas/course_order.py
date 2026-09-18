from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


OrderStatus = Literal["intent", "pending_payment", "paid", "cancelled", "completed"]


class CourseOrderCreate(BaseModel):
    external_order_id: str = Field(min_length=1, max_length=100)
    student_id: int | None = None
    course_name: str = Field(min_length=1, max_length=200)
    amount: Decimal = Field(default=Decimal("0.00"), ge=0, max_digits=12, decimal_places=2)
    status: OrderStatus = "intent"
    ordered_at: datetime | None = None


class CourseOrderUpdate(BaseModel):
    course_name: str | None = Field(default=None, min_length=1, max_length=200)
    amount: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    status: OrderStatus | None = None
    student_id: int | None = None


class CourseOrderRead(BaseModel):
    id: int
    external_order_id: str
    customer_id: int
    student_id: int | None
    course_name: str
    amount: Decimal
    status: str
    ordered_at: datetime
    raw_snapshot: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
