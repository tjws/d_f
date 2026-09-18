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
from app.models.organization import Organization
from app.models.student import Student
from app.models.timeline_event import TimelineEvent
from app.models.user import User


client = TestClient(app)


def _key() -> str:
    return base64.urlsafe_b64encode(b"a" * 32).decode("ascii")


def setup_function():
    with SessionLocal() as db:
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
    monkeypatch.setenv("APP_ENCRYPTION_KEY", _key())


@pytest.fixture
def auth_headers():
    register = client.post("/auth/register", json={"username": "suggestion_owner", "password": "Test123!"})
    assert register.status_code == 201
    login = client.post("/auth/token", data={"username": "suggestion_owner", "password": "Test123!"})
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _create_customer(headers: dict[str, str]) -> int:
    response = client.post("/customers", headers=headers, json={"name": "建议测试客户", "phone": "13800138000", "interested_subject": "英语"})
    assert response.status_code == 201
    return response.json()["id"]


def _confirm_profile(headers: dict[str, str], customer_id: int) -> int:
    draft = client.post(f"/customers/{customer_id}/profiles/draft", headers=headers)
    assert draft.status_code == 201
    profile_id = draft.json()["id"]
    confirmed = client.post(f"/customers/{customer_id}/profiles/{profile_id}/confirm", headers=headers)
    assert confirmed.status_code == 200
    return profile_id


def test_reply_suggestion_requires_human_acceptance(auth_headers):
    customer_id = _create_customer(auth_headers)
    profile_id = _confirm_profile(auth_headers, customer_id)

    generated = client.post(f"/customers/{customer_id}/suggestions/reply-draft", headers=auth_headers)
    assert generated.status_code == 201
    suggestion = generated.json()
    assert suggestion["status"] == "draft"
    assert suggestion["profile_id"] == profile_id
    assert suggestion["content"]["text"]
    assert suggestion["evidence"][0]["source_type"] == "customer_profile"

    edited = client.patch(f"/customers/{customer_id}/suggestions/{suggestion['id']}", headers=auth_headers, json={"content": {"text": "人工修改后的回复", "tone": "warm"}})
    assert edited.status_code == 200
    assert edited.json()["status"] == "edited"

    accepted = client.post(f"/customers/{customer_id}/suggestions/{suggestion['id']}/accept", headers=auth_headers)
    assert accepted.status_code == 200
    accepted_data = accepted.json()
    assert accepted_data["status"] == "accepted"
    assert accepted_data["edited_content"]["text"] == "人工修改后的回复"
    assert accepted_data["decided_by"] is not None

    accepted_again = client.post(f"/customers/{customer_id}/suggestions/{suggestion['id']}/accept", headers=auth_headers)
    assert accepted_again.status_code == 409


def test_reply_suggestion_includes_student_evidence(auth_headers):
    customer_id = _create_customer(auth_headers)
    student = client.post(
        f"/customers/{customer_id}/students",
        headers=auth_headers,
        json={"name": "小明", "grade": "初一", "school": "实验中学"},
    )
    assert student.status_code == 201
    _confirm_profile(auth_headers, customer_id)

    generated = client.post(f"/customers/{customer_id}/suggestions/reply-draft", headers=auth_headers)
    assert generated.status_code == 201
    evidence_types = {item["source_type"] for item in generated.json()["evidence"]}
    assert "student" in evidence_types


def test_reply_suggestion_requires_confirmed_profile(auth_headers):
    customer_id = _create_customer(auth_headers)
    response = client.post(f"/customers/{customer_id}/suggestions/reply-draft", headers=auth_headers)
    assert response.status_code == 409


def test_suggestion_endpoints_require_authentication():
    response = client.get("/customers/1/suggestions")
    assert response.status_code == 401
