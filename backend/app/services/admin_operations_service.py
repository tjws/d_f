from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.crypto import decrypt_text
from app.dao.admin_operations_dao import AdminOperationsDAO
from app.services.customer_service import customer_scope_filters


operations_dao = AdminOperationsDAO()
ORDER_STATUSES = {"intent", "pending_payment", "paid", "cancelled", "completed"}
TICKET_STATUSES = {"open", "in_progress", "resolved", "closed"}


def _validate_filter(value: str | None, allowed: set[str], label: str) -> str | None:
    if value is not None and value not in allowed:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"{label} 状态无效")
    return value


def get_admin_operations(db: Session, actor, order_status: str | None, ticket_status: str | None, limit: int) -> dict[str, list[dict[str, object]]]:
    order_status = _validate_filter(order_status, ORDER_STATUSES, "订单")
    ticket_status = _validate_filter(ticket_status, TICKET_STATUSES, "工单")
    scope_filters = customer_scope_filters(db, actor, "read")

    orders = []
    for order, customer, owner in operations_dao.list_orders(db, scope_filters, order_status, limit):
        orders.append(
            {
                "id": order.id,
                "external_order_id": order.external_order_id,
                "customer_id": customer.id,
                "customer_name": customer.name,
                "owner_name": owner.full_name or owner.username if owner else None,
                "course_name": order.course_name,
                "amount": order.amount,
                "status": order.status,
                "ordered_at": order.ordered_at,
            }
        )

    tickets = []
    for ticket, customer, owner in operations_dao.list_tickets(db, scope_filters, ticket_status, limit):
        tickets.append(
            {
                "id": ticket.id,
                "external_ticket_id": ticket.external_ticket_id,
                "customer_id": customer.id,
                "customer_name": customer.name,
                "owner_name": owner.full_name or owner.username if owner else None,
                "type": ticket.type,
                "status": ticket.status,
                "summary": decrypt_text(ticket.summary_encrypted),
                "opened_at": ticket.opened_at,
                "closed_at": ticket.closed_at,
            }
        )
    return {"orders": orders, "tickets": tickets}
