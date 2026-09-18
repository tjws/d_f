from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.crypto import encrypt_text
from app.dao.course_order_dao import CourseOrderDAO
from app.dao.service_ticket_dao import ServiceTicketDAO
from app.dao.timeline_event_dao import TimelineEventDAO
from app.integrations.operations.factory import get_operations_sync_provider
from app.models.course_order import CourseOrder
from app.models.service_ticket import ServiceTicket
from app.models.customer import Customer
from app.models.user import User
from app.schemas.admin_operations_sync import AdminOperationsSyncRequest
from app.schemas.course_order import CourseOrderCreate
from app.schemas.service_ticket import ServiceTicketCreate
from app.services.audit_log_service import append_audit_log
from app.services.course_order_service import _add_timeline as add_order_timeline, _validate_student
from app.services.customer_service import get_customer_or_404
from app.services.service_ticket_service import _add_timeline as add_ticket_timeline


order_dao = CourseOrderDAO()
ticket_dao = ServiceTicketDAO()


def sync_mock_operations(db: Session, actor: User, payload: AdminOperationsSyncRequest) -> dict[str, object]:
    """在一个事务内幂等导入 Mock 订单/工单，便于重放同步演练。"""

    get_customer_or_404(db, payload.customer_id, actor, "update")
    normalized = get_operations_sync_provider().normalize(payload.model_dump(mode="json"))
    orders_created = orders_skipped = tickets_created = tickets_skipped = 0

    for raw in normalized["orders"]:
        item = CourseOrderCreate.model_validate(raw)
        existing = order_dao.get_by_external_id(db, item.external_order_id)
        if existing:
            if existing.customer_id != payload.customer_id:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="外部订单编号已属于其他客户")
            orders_skipped += 1
            continue
        _validate_student(db, payload.customer_id, item.student_id)
        order = CourseOrder(
            customer_id=payload.customer_id,
            external_order_id=item.external_order_id,
            student_id=item.student_id,
            course_name=item.course_name,
            amount=item.amount,
            status=item.status,
            ordered_at=item.ordered_at or datetime.now(timezone.utc),
            raw_snapshot_json={"source": "mock_sync", "external_order_id": item.external_order_id, "status": item.status},
        )
        db.add(order)
        db.flush()
        if order.status == "paid":
            db.get(Customer, payload.customer_id).stage = "converted"
        add_order_timeline(db, payload.customer_id, actor.id, "order_synced", f"同步课程订单：{order.course_name}（{order.status}）", order.id)
        orders_created += 1

    for raw in normalized["tickets"]:
        item = ServiceTicketCreate.model_validate(raw)
        existing = ticket_dao.get_by_external_id(db, item.external_ticket_id)
        if existing:
            if existing.customer_id != payload.customer_id:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="外部工单编号已属于其他客户")
            tickets_skipped += 1
            continue
        ticket = ServiceTicket(
            customer_id=payload.customer_id,
            external_ticket_id=item.external_ticket_id,
            type=item.type,
            status=item.status,
            summary_encrypted=encrypt_text(item.summary),
            opened_at=item.opened_at or datetime.now(timezone.utc),
            closed_at=datetime.now(timezone.utc) if item.status == "closed" else None,
            raw_snapshot_json={"source": "mock_sync", "external_ticket_id": item.external_ticket_id, "status": item.status},
        )
        db.add(ticket)
        db.flush()
        add_ticket_timeline(db, payload.customer_id, actor.id, "service_ticket_synced", f"同步服务工单：{ticket.type}（{ticket.status}）", ticket.id)
        tickets_created += 1

    audit = append_audit_log(
        db,
        actor,
        "admin.operations_mock_synced",
        "customer",
        str(payload.customer_id),
        {"orders_created": orders_created, "orders_skipped": orders_skipped, "tickets_created": tickets_created, "tickets_skipped": tickets_skipped},
    )
    db.commit()
    return {
        "customer_id": payload.customer_id,
        "orders_created": orders_created,
        "orders_skipped": orders_skipped,
        "tickets_created": tickets_created,
        "tickets_skipped": tickets_skipped,
        "provider": "mock",
    }
