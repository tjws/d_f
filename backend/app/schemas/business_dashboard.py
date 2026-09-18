from datetime import datetime

from pydantic import BaseModel


class BusinessFunnelStage(BaseModel):
    stage: str
    count: int


class BusinessOrderMetrics(BaseModel):
    total: int
    by_status: dict[str, int]
    paid_or_completed: int
    paid_amount: float


class BusinessTicketMetrics(BaseModel):
    total: int
    by_status: dict[str, int]
    open_count: int


class BusinessOwnerMetric(BaseModel):
    user_id: int
    username: str
    full_name: str | None
    customer_count: int
    converted_customer_count: int
    paid_amount: float
    open_ticket_count: int


class BusinessDashboardRead(BaseModel):
    start: datetime
    end: datetime
    customer_total: int
    funnel: list[BusinessFunnelStage]
    orders: BusinessOrderMetrics
    tickets: BusinessTicketMetrics
    paying_customer_count: int
    repeat_purchase_customer_count: int
    renewal_rate: float
    renewal_rate_definition: str
    owner_efficiency: list[BusinessOwnerMetric]
