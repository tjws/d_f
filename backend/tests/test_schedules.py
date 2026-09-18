import base64

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.db.session import SessionLocal
from app.main import app
from app.models.ai_suggestion import AISuggestion
from app.models.audit_log import AuditLog
from app.models.customer import Customer
from app.models.customer_profile import CustomerProfile
from app.models.customer_tag import CustomerTag
from app.models.organization import Organization
from app.models.schedule import Schedule
from app.models.student import Student
from app.models.tag import Tag
from app.models.timeline_event import TimelineEvent
from app.models.user import User


client = TestClient(app)


def setup_function():
    with SessionLocal() as db:
        db.execute(delete(Schedule))
        db.execute(delete(CustomerTag))
        db.execute(delete(Tag))
        db.execute(delete(AISuggestion))
        db.execute(delete(CustomerProfile))
        db.execute(delete(TimelineEvent))
        db.execute(delete(AuditLog))
        db.execute(delete(Student))
        db.execute(delete(Organization))
        db.execute(delete(Customer))
        db.execute(delete(User))
        db.commit()


@pytest.fixture(autouse=True)
def encryption_key(monkeypatch):
    monkeypatch.setenv("APP_ENCRYPTION_KEY", base64.urlsafe_b64encode(b"h" * 32).decode("ascii"))


@pytest.fixture
def auth_headers():
    register = client.post("/auth/register", json={"username": "schedule_owner", "password": "Test123!"})
    assert register.status_code == 201
    login = client.post("/auth/token", data={"username": "schedule_owner", "password": "Test123!"})
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _create_customer(headers: dict[str, str]) -> int:
    response = client.post("/customers", headers=headers, json={"name": "日程测试客户", "phone": "13800138000", "interested_subject": "英语", "stage": "following_up"})
    assert response.status_code == 201
    return response.json()["id"]


def _confirm_profile(headers: dict[str, str], customer_id: int) -> None:
    draft = client.post(f"/customers/{customer_id}/profiles/draft", headers=headers)
    assert draft.status_code == 201
    confirmed = client.post(f"/customers/{customer_id}/profiles/{draft.json()['id']}/confirm", headers=headers)
    assert confirmed.status_code == 200


def test_schedule_suggestion_becomes_schedule_only_after_confirmation(auth_headers):
    customer_id = _create_customer(auth_headers)
    _confirm_profile(auth_headers, customer_id)

    generated = client.post(f"/customers/{customer_id}/schedule-suggestions", headers=auth_headers)
    assert generated.status_code == 201
    suggestion = generated.json()
    assert suggestion["suggestion_type"] == "schedule"
    assert suggestion["status"] == "draft"
    assert client.get(f"/customers/{customer_id}/schedules", headers=auth_headers).json() == []

    edited = client.patch(f"/customers/{customer_id}/schedule-suggestions/{suggestion['id']}", headers=auth_headers, json={"content": {**suggestion["content"], "title": "人工确认的英语回访", "priority": "high"}})
    assert edited.status_code == 200
    assert edited.json()["status"] == "edited"

    confirmed = client.post(f"/customers/{customer_id}/schedule-suggestions/{suggestion['id']}/confirm", headers=auth_headers)
    assert confirmed.status_code == 200
    schedule = confirmed.json()
    assert schedule["status"] == "confirmed"
    assert schedule["title"] == "人工确认的英语回访"
    assert schedule["wecom_calendar_id"] is None

    timeline = client.get(f"/customers/{customer_id}/timeline-events", headers=auth_headers)
    assert timeline.status_code == 200
    assert any(item["event_type"] == "schedule_created" for item in timeline.json())

    completed = client.post(f"/customers/{customer_id}/schedules/{schedule['id']}/complete", headers=auth_headers, json={"outcome": "appointment", "completion_note": "家长约好周末试听"})
    assert completed.status_code == 200
    assert completed.json()["status"] == "completed"
    assert completed.json()["outcome"] == "appointment"
    assert completed.json()["completion_note"] == "家长约好周末试听"
    cancelled = client.post(f"/customers/{customer_id}/schedules/{schedule['id']}/cancel", headers=auth_headers)
    assert cancelled.status_code == 409
    timeline_after_completion = client.get(f"/customers/{customer_id}/timeline-events", headers=auth_headers)
    assert any(item["event_type"] == "schedule_completed" for item in timeline_after_completion.json())


def test_schedule_suggestion_requires_confirmed_profile(auth_headers):
    customer_id = _create_customer(auth_headers)
    response = client.post(f"/customers/{customer_id}/schedule-suggestions", headers=auth_headers)
    assert response.status_code == 409


def test_schedule_endpoints_require_authentication():
    response = client.get("/customers/1/schedules")
    assert response.status_code == 401
