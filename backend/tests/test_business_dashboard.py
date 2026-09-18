import base64

from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.db.session import SessionLocal
from app.main import app
from app.models.ai_suggestion import AISuggestion
from app.models.ai_suggestion_feedback import AISuggestionFeedback
from app.models.ai_workflow_run import AIWorkflowRun
from app.models.audit_log import AuditLog
from app.models.chat_message import ChatMessage
from app.models.course_order import CourseOrder
from app.models.customer import Customer
from app.models.customer_profile import CustomerProfile
from app.models.customer_tag import CustomerTag
from app.models.customer_transfer import CustomerTransfer
from app.models.schedule import Schedule
from app.models.service_ticket import ServiceTicket
from app.models.student import Student
from app.models.tag import Tag
from app.models.timeline_event import TimelineEvent
from app.models.user import User


client = TestClient(app)


def setup_function():
    """每个测试重置业务事实，避免看板被其他测试数据污染。"""
    with SessionLocal() as db:
        for model in (
            ServiceTicket,
            CourseOrder,
            AISuggestionFeedback,
            AIWorkflowRun,
            Schedule,
            CustomerTag,
            Tag,
            AISuggestion,
            CustomerProfile,
            CustomerTransfer,
            ChatMessage,
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


def test_business_dashboard_aggregates_existing_facts_and_is_role_protected(monkeypatch):
    monkeypatch.setenv("APP_ENCRYPTION_KEY", base64.urlsafe_b64encode(b"b" * 32).decode("ascii"))
    admin_headers = _login_as("business_dashboard_admin", "admin")
    customer = client.post("/customers", headers=admin_headers, json={"name": "经营看板客户", "phone": "13800138001"})
    assert customer.status_code == 201
    customer_id = customer.json()["id"]

    first = client.post(
        f"/customers/{customer_id}/orders",
        headers=admin_headers,
        json={"external_order_id": "dashboard-order-001", "course_name": "数学课", "amount": "1200.00", "status": "paid"},
    )
    assert first.status_code == 201
    second = client.post(
        f"/customers/{customer_id}/orders",
        headers=admin_headers,
        json={"external_order_id": "dashboard-order-002", "course_name": "英语课", "amount": "800.00", "status": "pending_payment"},
    )
    assert second.status_code == 201
    paid = client.patch(f"/customers/{customer_id}/orders/{second.json()['id']}", headers=admin_headers, json={"status": "paid"})
    assert paid.status_code == 200
    ticket = client.post(
        f"/customers/{customer_id}/service-tickets",
        headers=admin_headers,
        json={"external_ticket_id": "dashboard-ticket-001", "type": "课程咨询", "summary": "需要安排试听"},
    )
    assert ticket.status_code == 201

    response = client.get("/admin/business-dashboard", headers=admin_headers)
    assert response.status_code == 200
    payload = response.json()
    assert payload["customer_total"] == 1
    assert payload["orders"]["paid_or_completed"] == 2
    assert payload["orders"]["paid_amount"] == 2000.0
    assert payload["paying_customer_count"] == 1
    assert payload["repeat_purchase_customer_count"] == 1
    assert payload["renewal_rate"] == 1.0
    assert {item["stage"]: item["count"] for item in payload["funnel"]}["converted"] == 1
    assert payload["tickets"]["open_count"] == 1

    sales_headers = _login_as("business_dashboard_sales", "sales")
    denied = client.get("/admin/business-dashboard", headers=sales_headers)
    assert denied.status_code == 403


def test_business_dashboard_rejects_an_unsafe_date_window(monkeypatch):
    monkeypatch.setenv("APP_ENCRYPTION_KEY", base64.urlsafe_b64encode(b"c" * 32).decode("ascii"))
    admin_headers = _login_as("business_dashboard_admin_range", "admin")
    response = client.get(
        "/admin/business-dashboard?start=2026-01-01T00:00:00Z&end=2026-02-15T00:00:00Z",
        headers=admin_headers,
    )
    assert response.status_code == 422
