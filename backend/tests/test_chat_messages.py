import base64

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select

from app.db.session import SessionLocal
from app.main import app
from app.models.audit_log import AuditLog
from app.models.chat_message import ChatMessage
from app.models.customer import Customer
from app.models.organization import Organization
from app.models.student import Student
from app.models.timeline_event import TimelineEvent
from app.models.user import User


client = TestClient(app)


def _key(seed: bytes = b"m" * 32) -> str:
    return base64.urlsafe_b64encode(seed).decode("ascii")


def setup_function():
    """每个聊天消息测试前清理相关数据。"""

    with SessionLocal() as db:
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
    register = client.post(
        "/auth/register",
        json={
            "username": "chat_owner",
            "password": "Test123!",
        },
    )
    assert register.status_code == 201

    login = client.post(
        "/auth/token",
        data={
            "username": "chat_owner",
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
            "name": "聊天消息测试客户",
            "phone": "13800138000",
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_create_list_and_deduplicate_chat_messages(auth_headers):
    customer_id = _create_customer(auth_headers)
    content = "家长电话 13800138000，想了解初一数学课程"
    payload = {
        "wecom_message_id": "mock-msg-001",
        "direction": "inbound",
        "message_type": "text",
        "content": content,
    }

    create_response = client.post(
        f"/customers/{customer_id}/chat-messages/mock",
        headers=auth_headers,
        json=payload,
    )

    assert create_response.status_code == 201
    body = create_response.json()
    assert body["content"] == content
    assert body["content_masked"] == (
        "家长电话 138****8000，想了解初一数学课程"
    )

    with SessionLocal() as db:
        message = db.scalar(select(ChatMessage))
        assert message is not None
        assert message.content_encrypted != content
        assert content not in message.content_encrypted
        assert db.scalar(select(func.count(TimelineEvent.id))) == 1

    duplicate_response = client.post(
        f"/customers/{customer_id}/chat-messages/mock",
        headers=auth_headers,
        json=payload,
    )
    assert duplicate_response.status_code == 200

    with SessionLocal() as db:
        assert db.scalar(select(func.count(ChatMessage.id))) == 1
        assert db.scalar(select(func.count(TimelineEvent.id))) == 1

    list_response = client.get(
        f"/customers/{customer_id}/chat-messages",
        headers=auth_headers,
    )
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1
    assert list_response.json()[0]["content"] == content


def test_chat_messages_require_authentication():
    response = client.get("/customers/1/chat-messages")

    assert response.status_code == 401


def test_user_cannot_access_another_users_chat_messages(auth_headers):
    customer_id = _create_customer(auth_headers)

    other_register = client.post(
        "/auth/register",
        json={
            "username": "other_chat_user",
            "password": "Test123!",
        },
    )
    assert other_register.status_code == 201

    other_login = client.post(
        "/auth/token",
        data={
            "username": "other_chat_user",
            "password": "Test123!",
        },
    )
    other_headers = {
        "Authorization": f"Bearer {other_login.json()['access_token']}"
    }

    get_response = client.get(
        f"/customers/{customer_id}/chat-messages",
        headers=other_headers,
    )
    create_response = client.post(
        f"/customers/{customer_id}/chat-messages/mock",
        headers=other_headers,
        json={
            "wecom_message_id": "cross-user-msg",
            "direction": "inbound",
            "message_type": "text",
            "content": "越权消息",
        },
    )

    assert get_response.status_code == 404
    assert create_response.status_code == 404
