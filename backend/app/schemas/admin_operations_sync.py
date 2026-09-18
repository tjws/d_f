from pydantic import BaseModel, Field

from app.schemas.course_order import CourseOrderCreate
from app.schemas.service_ticket import ServiceTicketCreate


class AdminOperationsSyncRequest(BaseModel):
    customer_id: int = Field(ge=1)
    orders: list[CourseOrderCreate] = Field(default_factory=list, max_length=100)
    tickets: list[ServiceTicketCreate] = Field(default_factory=list, max_length=100)


class AdminOperationsSyncRead(BaseModel):
    customer_id: int
    orders_created: int
    orders_skipped: int
    tickets_created: int
    tickets_skipped: int
    provider: str
