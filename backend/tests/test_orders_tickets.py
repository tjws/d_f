import base64

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.db.session import SessionLocal
from app.main import app
from app.models.ai_suggestion import AISuggestion
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
    with SessionLocal() as db:
        for model in (ServiceTicket, CourseOrder, CustomerTag, Tag, AISuggestion, CustomerProfile, TimelineEvent, Student, AuditLog, Customer, User):
            db.execute(delete(model))
        db.commit()


@pytest.fixture(autouse=True)
def encryption_key(monkeypatch):
    monkeypatch.setenv("APP_ENCRYPTION_KEY", base64.urlsafe_b64encode(b"o" * 32).decode("ascii"))


@pytest.fixture
def auth_headers():
    assert client.post("/auth/register", json={"username": "order_owner", "password": "Test123!"}).status_code == 201
    login = client.post("/auth/token", data={"username": "order_owner", "password": "Test123!"})
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _customer(headers: dict[str, str]) -> int:
    response = client.post("/customers", headers=headers, json={"name": "订单工单客户", "phone": "13800138000"})
    assert response.status_code == 201
    return response.json()["id"]


def test_order_paid_updates_customer_and_timeline(auth_headers):
    customer_id = _customer(auth_headers)
    student = client.post(f"/customers/{customer_id}/students", headers=auth_headers, json={"name": "测试学生", "grade": "初一"})
    assert student.status_code == 201
    order = client.post(f"/customers/{customer_id}/orders", headers=auth_headers, json={"external_order_id": "mock-order-001", "student_id": student.json()["id"], "course_name": "数学提升课", "amount": "1999.00", "status": "pending_payment"})
    assert order.status_code == 201
    paid = client.patch(f"/customers/{customer_id}/orders/{order.json()['id']}", headers=auth_headers, json={"status": "paid"})
    assert paid.status_code == 200
    assert paid.json()["amount"] == "1999.00"
    customer = client.get(f"/customers/{customer_id}", headers=auth_headers)
    assert customer.json()["stage"] == "converted"
    timeline = client.get(f"/customers/{customer_id}/timeline-events", headers=auth_headers).json()
    assert {item["event_type"] for item in timeline} >= {"order_created", "order_status_changed"}


def test_ticket_summary_is_returned_and_status_is_guarded(auth_headers):
    customer_id = _customer(auth_headers)
    created = client.post(f"/customers/{customer_id}/service-tickets", headers=auth_headers, json={"external_ticket_id": "mock-ticket-001", "type": "课程咨询", "summary": "家长希望调整上课时间"})
    assert created.status_code == 201
    ticket_id = created.json()["id"]
    assert created.json()["summary"] == "家长希望调整上课时间"
    moved = client.patch(f"/customers/{customer_id}/service-tickets/{ticket_id}", headers=auth_headers, json={"status": "in_progress"})
    assert moved.status_code == 200
    closed = client.patch(f"/customers/{customer_id}/service-tickets/{ticket_id}", headers=auth_headers, json={"status": "closed"})
    assert closed.status_code == 200
    assert closed.json()["closed_at"] is not None
    invalid = client.patch(f"/customers/{customer_id}/service-tickets/{ticket_id}", headers=auth_headers, json={"status": "open"})
    assert invalid.status_code == 409
    duplicate = client.post(f"/customers/{customer_id}/service-tickets", headers=auth_headers, json={"external_ticket_id": "mock-ticket-001", "summary": "重复工单"})
    assert duplicate.status_code == 409


def test_order_and_ticket_endpoints_require_authentication():
    assert client.get("/customers/1/orders").status_code == 401
    assert client.get("/customers/1/service-tickets").status_code == 401
