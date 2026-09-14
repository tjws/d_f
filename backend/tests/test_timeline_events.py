import base64

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.db.session import SessionLocal
from app.main import app
from app.models.audit_log import AuditLog
from app.models.customer import Customer
from app.models.organization import Organization
from app.models.student import Student
from app.models.timeline_event import TimelineEvent
from app.models.user import User


client = TestClient(app)


def _key(seed: bytes = b"t" * 32) -> str:
    return base64.urlsafe_b64encode(seed).decode("ascii")


def setup_function():
    """每个时间线测试前清理相关数据，避免测试相互影响。"""

    with SessionLocal() as db:
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
    register = client.post(
        "/auth/register",
        json={
            "username": "timeline_owner",
            "password": "Test123!",
        },
    )
    assert register.status_code == 201

    login = client.post(
        "/auth/token",
        data={
            "username": "timeline_owner",
            "password": "Test123!",
        },
    )
    assert login.status_code == 200

    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _create_customer(headers: dict[str, str]) -> int:
    response = client.post(
        "/customers",
        headers=headers,
        json={
            "name": "时间线测试客户",
            "phone": "13800138000",
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_create_and_list_timeline_events(auth_headers):
    customer_id = _create_customer(auth_headers)
    summary = "家长确认周末参加数学试听课"

    create_response = client.post(
        f"/customers/{customer_id}/timeline-events",
        headers=auth_headers,
        json={
            "event_type": "manual_follow_up",
            "summary": summary,
            "reference_type": "customer",
            "reference_id": str(customer_id),
        },
    )

    assert create_response.status_code == 201
    body = create_response.json()
    assert body["summary"] == summary
    assert body["source"] == "manual"
    assert body["operator_id"] is not None

    with SessionLocal() as db:
        event = db.scalar(select(TimelineEvent))
        assert event is not None
        assert event.summary_encrypted != summary
        assert summary not in event.summary_encrypted

    list_response = client.get(
        f"/customers/{customer_id}/timeline-events",
        headers=auth_headers,
    )

    assert list_response.status_code == 200
    assert len(list_response.json()) == 1
    assert list_response.json()[0]["summary"] == summary


def test_timeline_events_require_authentication():
    response = client.get("/customers/1/timeline-events")

    assert response.status_code == 401


def test_user_cannot_access_another_users_timeline(auth_headers):
    customer_id = _create_customer(auth_headers)

    other_register = client.post(
        "/auth/register",
        json={
            "username": "other_timeline_user",
            "password": "Test123!",
        },
    )
    assert other_register.status_code == 201

    other_login = client.post(
        "/auth/token",
        data={
            "username": "other_timeline_user",
            "password": "Test123!",
        },
    )
    other_headers = {
        "Authorization": f"Bearer {other_login.json()['access_token']}"
    }

    get_response = client.get(
        f"/customers/{customer_id}/timeline-events",
        headers=other_headers,
    )
    create_response = client.post(
        f"/customers/{customer_id}/timeline-events",
        headers=other_headers,
        json={
            "event_type": "manual_follow_up",
            "summary": "越权事件",
        },
    )

    assert get_response.status_code == 404
    assert create_response.status_code == 404
