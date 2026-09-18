from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.crypto import decrypt_text, encrypt_text
from app.dao.service_ticket_dao import ServiceTicketDAO
from app.dao.timeline_event_dao import TimelineEventDAO
from app.models.service_ticket import ServiceTicket
from app.models.timeline_event import TimelineEvent
from app.models.user import User
from app.schemas.service_ticket import ServiceTicketCreate, ServiceTicketUpdate
from app.services.audit_log_service import append_audit_log
from app.services.customer_service import get_customer_or_404


ticket_dao = ServiceTicketDAO()
timeline_dao = TimelineEventDAO()
TICKET_TRANSITIONS = {
    "open": {"in_progress", "resolved", "closed"},
    "in_progress": {"resolved", "closed"},
    "resolved": {"closed", "in_progress"},
    "closed": set(),
}


def _add_timeline(db: Session, customer_id: int, actor_id: int, event_type: str, summary: str, reference_id: int) -> None:
    timeline_dao.add(db, TimelineEvent(customer_id=customer_id, operator_id=actor_id, occurred_at=datetime.now(timezone.utc), event_type=event_type, summary_encrypted=encrypt_text(summary), source="system", reference_type="service_ticket", reference_id=str(reference_id)))


def to_ticket_read(ticket: ServiceTicket) -> dict:
    return {
        "id": ticket.id,
        "external_ticket_id": ticket.external_ticket_id,
        "customer_id": ticket.customer_id,
        "type": ticket.type,
        "status": ticket.status,
        "summary": decrypt_text(ticket.summary_encrypted),
        "opened_at": ticket.opened_at,
        "closed_at": ticket.closed_at,
        "raw_snapshot": ticket.raw_snapshot_json,
        "created_at": ticket.created_at,
        "updated_at": ticket.updated_at,
    }


def create_ticket(db: Session, customer_id: int, actor: User, payload: ServiceTicketCreate) -> ServiceTicket:
    get_customer_or_404(db, customer_id, actor, "update")
    if ticket_dao.get_by_external_id(db, payload.external_ticket_id) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="外部工单编号已存在")
    ticket = ServiceTicket(customer_id=customer_id, external_ticket_id=payload.external_ticket_id, type=payload.type, status=payload.status, summary_encrypted=encrypt_text(payload.summary), opened_at=payload.opened_at or datetime.now(timezone.utc), closed_at=datetime.now(timezone.utc) if payload.status == "closed" else None, raw_snapshot_json={"source": "mock", "external_ticket_id": payload.external_ticket_id, "status": payload.status})
    ticket_dao.add(db, ticket)
    db.flush()
    _add_timeline(db, customer_id, actor.id, "service_ticket_created", f"创建服务工单：{ticket.type}（{ticket.status}）", ticket.id)
    append_audit_log(db, actor, "customer.service_ticket_created", "service_ticket", str(ticket.id), {"status": ticket.status, "type": ticket.type})
    db.commit()
    db.refresh(ticket)
    return ticket


def list_tickets(db: Session, customer_id: int, actor: User) -> list[ServiceTicket]:
    get_customer_or_404(db, customer_id, actor, "read")
    return ticket_dao.list_by_customer(db, customer_id)


def update_ticket(db: Session, customer_id: int, ticket_id: int, actor: User, payload: ServiceTicketUpdate) -> ServiceTicket:
    get_customer_or_404(db, customer_id, actor, "update")
    ticket = ticket_dao.get_by_id(db, customer_id, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="服务工单不存在")
    changes = payload.model_dump(exclude_unset=True)
    old_status = ticket.status
    new_status = changes.get("status", old_status)
    if new_status != old_status and new_status not in TICKET_TRANSITIONS.get(old_status, set()):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"工单不能从 {old_status} 变更为 {new_status}")
    if "summary" in changes:
        ticket.summary_encrypted = encrypt_text(changes.pop("summary"))
    for field, value in changes.items():
        setattr(ticket, field, value)
    if ticket.status == "closed" and ticket.closed_at is None:
        ticket.closed_at = datetime.now(timezone.utc)
    elif ticket.status != "closed":
        ticket.closed_at = None
    if ticket.status != old_status:
        _add_timeline(db, customer_id, actor.id, "service_ticket_status_changed", f"工单 {ticket.type} 状态：{old_status} → {ticket.status}", ticket.id)
    append_audit_log(db, actor, "customer.service_ticket_updated", "service_ticket", str(ticket.id), {"old_status": old_status, "status": ticket.status})
    db.commit()
    db.refresh(ticket)
    return ticket
