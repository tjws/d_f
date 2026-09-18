from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class AdminOrderRead(BaseModel):
    id: int
    external_order_id: str
    customer_id: int
    customer_name: str
    owner_name: str | None
    course_name: str
    amount: Decimal
    status: str
    ordered_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AdminTicketRead(BaseModel):
    id: int
    external_ticket_id: str
    customer_id: int
    customer_name: str
    owner_name: str | None
    type: str
    status: str
    summary: str
    opened_at: datetime
    closed_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class AdminOperationsRead(BaseModel):
    orders: list[AdminOrderRead]
    tickets: list[AdminTicketRead]
