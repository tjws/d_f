from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.service_ticket import ServiceTicketCreate, ServiceTicketRead, ServiceTicketUpdate
from app.services.service_ticket_service import create_ticket, list_tickets, to_ticket_read, update_ticket


router = APIRouter(prefix="/customers/{customer_id}/service-tickets", tags=["service-tickets"])


@router.post("", response_model=ServiceTicketRead, status_code=status.HTTP_201_CREATED)
def create_customer_service_ticket(customer_id: int, payload: ServiceTicketCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return to_ticket_read(create_ticket(db, customer_id, current_user, payload))


@router.get("", response_model=list[ServiceTicketRead])
def get_customer_service_tickets(customer_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return [to_ticket_read(ticket) for ticket in list_tickets(db, customer_id, current_user)]


@router.patch("/{ticket_id}", response_model=ServiceTicketRead)
def edit_customer_service_ticket(customer_id: int, ticket_id: int, payload: ServiceTicketUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return to_ticket_read(update_ticket(db, customer_id, ticket_id, current_user, payload))
