from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.db.session import SessionLocal
from app.main import app
from app.models.audit_log import AuditLog
from app.models.course_order import CourseOrder
from app.models.customer import Customer
from app.models.customer_profile import CustomerProfile
from app.models.customer_tag import CustomerTag
from app.models.service_ticket import ServiceTicket
from app.models.student import Student
from app.models.tag import Tag
from app.models.timeline_event import TimelineEvent
from app.models.user import User


client = TestClient(app)


def setup_function():
    """清理本模块创建的业务数据，避免测试之间互相污染。"""
    with SessionLocal() as db:
        for model in (
            ServiceTicket,
            CourseOrder,
            CustomerTag,
            Tag,
            CustomerProfile,
            TimelineEvent,
            Student,
            AuditLog,
            Customer,
            User,
        ):
            db.execute(delete(model))
        db.commit()


def _login_as(username: str, role: str) -> dict[str, str]:
    password = "Test123!"
    registered = client.post("/auth/register", json={"username": username, "password": password})
    assert registered.status_code == 201
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.username == username))
        assert user is not None
        user.role = role
        db.commit()
    login = client.post("/auth/token", data={"username": username, "password": password})
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def test_admin_operations_lists_orders_tickets_and_applies_filters():
    headers = _login_as("operations_admin", "admin")
    customer = client.post("/customers", headers=headers, json={"name": "管理台客户", "phone": "13800138010"})
    assert customer.status_code == 201
    customer_id = customer.json()["id"]

    order = client.post(
        f"/customers/{customer_id}/orders",
        headers=headers,
        json={
            "external_order_id": "admin-order-001",
            "course_name": "数学提升课",
            "amount": "1999.00",
            "status": "paid",
        },
    )
    assert order.status_code == 201
    ticket = client.post(
        f"/customers/{customer_id}/service-tickets",
        headers=headers,
        json={
            "external_ticket_id": "admin-ticket-001",
            "type": "课程咨询",
            "summary": "家长希望调整课程时间",
            "status": "open",
        },
    )
    assert ticket.status_code == 201

    listed = client.get("/admin/operations", headers=headers)
    assert listed.status_code == 200
    assert listed.json()["orders"][0]["external_order_id"] == "admin-order-001"
    assert listed.json()["orders"][0]["customer_name"] == "管理台客户"
    assert listed.json()["tickets"][0]["summary"] == "家长希望调整课程时间"

    filtered = client.get(
        "/admin/operations?order_status=paid&ticket_status=open&limit=1",
        headers=headers,
    )
    assert filtered.status_code == 200
    assert len(filtered.json()["orders"]) == 1
    assert len(filtered.json()["tickets"]) == 1

    invalid = client.get("/admin/operations?order_status=unknown", headers=headers)
    assert invalid.status_code == 422


def test_admin_operations_allows_manager_read_and_denies_sales():
    manager_headers = _login_as("operations_manager", "manager")
    sales_headers = _login_as("operations_sales", "sales")
    assert client.get("/admin/operations", headers=manager_headers).status_code == 200
    denied = client.get("/admin/operations", headers=sales_headers)
    assert denied.status_code == 403
