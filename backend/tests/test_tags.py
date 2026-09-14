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
from app.models.student import Student
from app.models.tag import Tag
from app.models.timeline_event import TimelineEvent
from app.models.user import User


client = TestClient(app)


def setup_function():
    with SessionLocal() as db:
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
    monkeypatch.setenv("APP_ENCRYPTION_KEY", base64.urlsafe_b64encode(b"g" * 32).decode("ascii"))


@pytest.fixture
def auth_headers():
    register = client.post("/auth/register", json={"username": "tag_owner", "password": "Test123!"})
    assert register.status_code == 201
    login = client.post("/auth/token", data={"username": "tag_owner", "password": "Test123!"})
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _create_customer(headers: dict[str, str]) -> int:
    response = client.post("/customers", headers=headers, json={"name": "标签测试客户", "phone": "13800138000", "interested_subject": "数学", "stage": "following_up"})
    assert response.status_code == 201
    return response.json()["id"]


def test_tag_suggestions_need_human_confirmation(auth_headers):
    customer_id = _create_customer(auth_headers)
    generated = client.post(f"/customers/{customer_id}/tags/suggestions", headers=auth_headers)
    assert generated.status_code == 200
    suggestions = generated.json()
    assert len(suggestions) == 2
    assert {item["status"] for item in suggestions} == {"suggested"}
    assert {item["tag"]["key"] for item in suggestions} == {"subject_math", "follow_up_active"}

    confirmed = client.post(f"/customers/{customer_id}/tags/{suggestions[0]['id']}/confirm", headers=auth_headers)
    assert confirmed.status_code == 200
    assert confirmed.json()["status"] == "confirmed"
    assert confirmed.json()["confirmed_by"] is not None

    rejected = client.post(f"/customers/{customer_id}/tags/{suggestions[1]['id']}/reject", headers=auth_headers)
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"

    repeated = client.post(f"/customers/{customer_id}/tags/suggestions", headers=auth_headers)
    assert repeated.status_code == 200
    assert any(item["status"] == "confirmed" for item in repeated.json())


def test_tag_catalog_and_customer_tags_require_authentication():
    assert client.get("/tags").status_code == 401
    assert client.get("/customers/1/tags").status_code == 401
