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


@pytest.fixture(autouse=True)
def encryption_key(monkeypatch):
    monkeypatch.setenv(
        "APP_ENCRYPTION_KEY",
        base64.urlsafe_b64encode(b"b" * 32).decode("ascii"),
    )


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


def test_ai_workflow_endpoint_persists_draft_and_requires_authentication():
    register = client.post(
        "/auth/register",
        json={"username": "workflow_owner", "password": "Test123!"},
    )
    assert register.status_code == 201
    login = client.post(
        "/auth/token",
        data={"username": "workflow_owner", "password": "Test123!"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    customer = client.post(
        "/customers",
        headers=headers,
        json={"name": "Workflow 客户", "phone": "13800990000", "interested_subject": "英语"},
    )
    customer_id = customer.json()["id"]
    draft = client.post(f"/customers/{customer_id}/profiles/draft", headers=headers)
    assert draft.status_code == 201
    confirmed = client.post(
        f"/customers/{customer_id}/profiles/{draft.json()['id']}/confirm",
        headers=headers,
    )
    assert confirmed.status_code == 200

    response = client.post(
        f"/customers/{customer_id}/ai-workflow",
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "waiting_human"
    assert len(response.json()["suggestion_ids"]) == 1

    suggestions = client.get(
        f"/customers/{customer_id}/suggestions",
        headers=headers,
    )
    assert suggestions.status_code == 200
    assert suggestions.json()[0]["status"] == "draft"

    unauthenticated = client.post(f"/customers/{customer_id}/ai-workflow")
    assert unauthenticated.status_code == 401
