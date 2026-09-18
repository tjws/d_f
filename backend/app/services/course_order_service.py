from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.crypto import encrypt_text
from app.dao.course_order_dao import CourseOrderDAO
from app.dao.timeline_event_dao import TimelineEventDAO
from app.models.course_order import CourseOrder
from app.models.student import Student
from app.models.timeline_event import TimelineEvent
from app.models.user import User
from app.schemas.course_order import CourseOrderCreate, CourseOrderUpdate
from app.services.audit_log_service import append_audit_log
from app.services.customer_service import get_customer_or_404


order_dao = CourseOrderDAO()
timeline_dao = TimelineEventDAO()
ORDER_TRANSITIONS = {
    "intent": {"pending_payment", "cancelled"},
    "pending_payment": {"paid", "cancelled"},
    "paid": {"completed", "cancelled"},
    "completed": set(),
    "cancelled": set(),
}


def _validate_student(db: Session, customer_id: int, student_id: int | None) -> None:
    if student_id is None:
        return
    student = db.get(Student, student_id)
    if student is None or student.customer_id != customer_id or student.archived_at is not None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="学生不存在或不属于当前客户")


def _add_timeline(db: Session, customer_id: int, actor_id: int, event_type: str, summary: str, reference_id: int) -> None:
    timeline_dao.add(db, TimelineEvent(customer_id=customer_id, operator_id=actor_id, occurred_at=datetime.now(timezone.utc), event_type=event_type, summary_encrypted=encrypt_text(summary), source="system", reference_type="course_order", reference_id=str(reference_id)))


def to_order_read(order: CourseOrder) -> dict:
    return {
        "id": order.id,
        "external_order_id": order.external_order_id,
        "customer_id": order.customer_id,
        "student_id": order.student_id,
        "course_name": order.course_name,
        "amount": order.amount,
        "status": order.status,
        "ordered_at": order.ordered_at,
        "raw_snapshot": order.raw_snapshot_json,
        "created_at": order.created_at,
        "updated_at": order.updated_at,
    }


def create_order(db: Session, customer_id: int, actor: User, payload: CourseOrderCreate) -> CourseOrder:
    get_customer_or_404(db, customer_id, actor, "update")
    if order_dao.get_by_external_id(db, payload.external_order_id) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="外部订单编号已存在")
    _validate_student(db, customer_id, payload.student_id)
    order = CourseOrder(customer_id=customer_id, external_order_id=payload.external_order_id, student_id=payload.student_id, course_name=payload.course_name, amount=payload.amount, status=payload.status, ordered_at=payload.ordered_at or datetime.now(timezone.utc), raw_snapshot_json={"source": "mock", "external_order_id": payload.external_order_id, "status": payload.status})
    order_dao.add(db, order)
    db.flush()
    if order.status == "paid":
        customer = get_customer_or_404(db, customer_id, actor, "update")
        customer.stage = "converted"
    _add_timeline(db, customer_id, actor.id, "order_created", f"创建课程订单：{order.course_name}（{order.status}）", order.id)
    append_audit_log(db, actor, "customer.order_created", "course_order", str(order.id), {"status": order.status, "amount": str(order.amount)})
    db.commit()
    db.refresh(order)
    return order


def list_orders(db: Session, customer_id: int, actor: User) -> list[CourseOrder]:
    get_customer_or_404(db, customer_id, actor, "read")
    return order_dao.list_by_customer(db, customer_id)


def update_order(db: Session, customer_id: int, order_id: int, actor: User, payload: CourseOrderUpdate) -> CourseOrder:
    get_customer_or_404(db, customer_id, actor, "update")
    order = order_dao.get_by_id(db, customer_id, order_id)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="订单不存在")
    _validate_student(db, customer_id, payload.student_id)
    old_status = order.status
    changes = payload.model_dump(exclude_unset=True)
    if "status" in changes and changes["status"] != old_status and changes["status"] not in ORDER_TRANSITIONS.get(old_status, set()):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"订单不能从 {old_status} 变更为 {changes['status']}")
    for field, value in changes.items():
        setattr(order, field, value)
    if order.status == "paid" and old_status != "paid":
        customer = get_customer_or_404(db, customer_id, actor, "update")
        customer.stage = "converted"
    if order.status != old_status:
        _add_timeline(db, customer_id, actor.id, "order_status_changed", f"订单 {order.course_name} 状态：{old_status} → {order.status}", order.id)
    append_audit_log(db, actor, "customer.order_updated", "course_order", str(order.id), {"old_status": old_status, "status": order.status})
    db.commit()
    db.refresh(order)
    return order
