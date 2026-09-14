import base64

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.db.session import SessionLocal
from app.main import app
from app.models.audit_log import AuditLog
from app.models.chat_message import ChatMessage
from app.models.customer import Customer
from app.models.customer_profile import CustomerProfile
from app.models.organization import Organization
from app.models.student import Student
from app.models.timeline_event import TimelineEvent
from app.models.user import User


client = TestClient(app)


def _key() -> str:
    return base64.urlsafe_b64encode(b"p" * 32).decode("ascii")


def setup_function():
    with SessionLocal() as db:
        db.execute(delete(CustomerProfile))
        db.execute(delete(ChatMessage))
        db.execute(delete(TimelineEvent))
        db.execute(delete(AuditLog))
        db.execute(delete(Student))
        db.execute(delete(Organization))
        db.execute(delete(Customer))
        db.execute(delete(User))
        db.commit()


@pytest.fixture(autouse=True)
def encryption_key(monkeypatch):
    monkeypatch.setenv("APP_ENCRYPTION_KEY", _key())


@pytest.fixture
def auth_headers():
    register = client.post("/auth/register", json={"username": "profile_owner", "password": "Test123!"})
    assert register.status_code == 201
    login = client.post("/auth/token", data={"username": "profile_owner", "password": "Test123!"})
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _create_customer(headers: dict[str, str]) -> int:
    response = client.post("/customers", headers=headers, json={"name": "画像测试客户", "phone": "13800138000", "stage": "following_up", "interested_subject": "数学"})
    assert response.status_code == 201
    return response.json()["id"]


def test_profile_draft_can_be_edited_and_confirmed(auth_headers):
    customer_id = _create_customer(auth_headers)
    student = client.post(f"/customers/{customer_id}/students", headers=auth_headers, json={"name": "小明", "grade": "小学五年级", "school": "测试学校"})
    assert student.status_code == 201
    event = client.post(f"/customers/{customer_id}/timeline-events", headers=auth_headers, json={"event_type": "manual_follow_up", "summary": "家长希望了解数学课程"})
    assert event.status_code == 201
    message = client.post(f"/customers/{customer_id}/chat-messages/mock", headers=auth_headers, json={"wecom_message_id": "profile-msg-001", "direction": "inbound", "message_type": "text", "content": "请介绍数学课程"})
    assert message.status_code == 201

    draft = client.post(f"/customers/{customer_id}/profiles/draft", headers=auth_headers)
    assert draft.status_code == 201
    draft_data = draft.json()
    assert draft_data["status"] == "draft"
    assert draft_data["dimensions"]["student_count"] == 1
    assert {item["source_type"] for item in draft_data["evidence"]} == {"student", "timeline_event", "chat_message"}

    edited = client.patch(f"/customers/{customer_id}/profiles/{draft_data['id']}", headers=auth_headers, json={"dimensions": {"summary": "人工确认后的重点", "next_action": "安排试听"}})
    assert edited.status_code == 200
    assert edited.json()["dimensions"]["next_action"] == "安排试听"

    confirmed = client.post(f"/customers/{customer_id}/profiles/{draft_data['id']}/confirm", headers=auth_headers)
    assert confirmed.status_code == 200
    assert confirmed.json()["status"] == "confirmed"
    assert confirmed.json()["confirmed_by"] is not None

    second_edit = client.patch(f"/customers/{customer_id}/profiles/{draft_data['id']}", headers=auth_headers, json={"dimensions": {"summary": "不应覆盖已确认版本"}})
    assert second_edit.status_code == 409


def test_only_draft_profile_can_be_rejected(auth_headers):
    customer_id = _create_customer(auth_headers)
    draft = client.post(f"/customers/{customer_id}/profiles/draft", headers=auth_headers)
    assert draft.status_code == 201
    profile_id = draft.json()["id"]
    rejected = client.post(f"/customers/{customer_id}/profiles/{profile_id}/reject", headers=auth_headers)
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"
    confirmed = client.post(f"/customers/{customer_id}/profiles/{profile_id}/confirm", headers=auth_headers)
    assert confirmed.status_code == 409


def test_profile_endpoints_require_authentication():
    response = client.get("/customers/1/profiles")
    assert response.status_code == 401
