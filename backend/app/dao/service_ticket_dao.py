from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.service_ticket import ServiceTicket


class ServiceTicketDAO:
    def get_by_id(self, db: Session, customer_id: int, ticket_id: int) -> ServiceTicket | None:
        return db.scalar(select(ServiceTicket).where(ServiceTicket.customer_id == customer_id, ServiceTicket.id == ticket_id))

    def get_by_external_id(self, db: Session, external_ticket_id: str) -> ServiceTicket | None:
        return db.scalar(select(ServiceTicket).where(ServiceTicket.external_ticket_id == external_ticket_id))

    def list_by_customer(self, db: Session, customer_id: int) -> list[ServiceTicket]:
        return list(db.scalars(select(ServiceTicket).where(ServiceTicket.customer_id == customer_id).order_by(ServiceTicket.opened_at.desc(), ServiceTicket.id.desc())).all())

    def add(self, db: Session, ticket: ServiceTicket) -> None:
        db.add(ticket)
