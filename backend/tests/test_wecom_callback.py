import base64
import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.integrations.wecom.callback import (
    DatabaseCallbackProcessor,
    MockCallbackProcessor,
    build_mock_signature,
    verify_mock_signature,
)
from app.models.integration_event import IntegrationEvent
from app.models.audit_log import AuditLog
from app.models.chat_message import ChatMessage
from app.models.customer import Customer
from app.models.organization import Organization
from app.models.timeline_event import TimelineEvent
from app.models.user import User
from app.main import app


client = TestClient(app)


@pytest.fixture(autouse=True)
def encryption_key(monkeypatch):
    """回调原文和聊天正文都必须使用测试密钥加密。"""

    monkeypatch.setenv(
        "APP_ENCRYPTION_KEY",
        base64.urlsafe_b64encode(b"w" * 32).decode("ascii"),
    )


def setup_function():
    """清理数据库事件，保证每次测试从空状态开始。"""

    with SessionLocal() as db:
        db.execute(
            delete(ChatMessage).where(
                ChatMessage.wecom_message_id.like("callback-msg-%")
            )
        )
        db.execute(
            delete(TimelineEvent).where(
                TimelineEvent.reference_type == "chat_message",
                TimelineEvent.reference_id.like("callback-msg-%"),
            )
        )
        db.execute(
            delete(Customer).where(
                Customer.phone == "13700000000"
            )
        )
        db.execute(delete(AuditLog))
        db.execute(delete(IntegrationEvent))
        db.execute(
            delete(User).where(User.wecom_userid.like("http-user-%"))
        )
        # 清理聊天回调测试专用用户，避免唯一 wecom_userid 影响重复运行。
        db.execute(
            delete(User).where(User.wecom_userid == "callback-chat-user")
        )
        db.execute(delete(User).where(User.username == "conflict_sales"))
        db.execute(delete(User).where(User.username == "existing_manager"))
        db.execute(delete(Organization))
        db.commit()


def test_mock_callback_signature_can_be_verified():
    """正确签名可以通过验证，篡改内容不能通过。"""

    token = "test-token"
    timestamp = "1700000000"
    nonce = "abc123"
    body = '{"event":"user_auth"}'

    signature = build_mock_signature(
        token,
        timestamp,
        nonce,
        body,
    )

    assert verify_mock_signature(
        token,
        timestamp,
        nonce,
        body,
        signature,
    ) is True

    assert verify_mock_signature(
        token,
        timestamp,
        nonce,
        '{"event":"tampered"}',
        signature,
    ) is False


def test_mock_callback_is_idempotent():
    """同一个成功事件重复到达时只处理一次。"""

    processor = MockCallbackProcessor()
    calls = []

    def handler():
        calls.append("handled")

    assert processor.process("event-001", handler) == "processed"
    assert processor.process("event-001", handler) == "duplicate"
    assert calls == ["handled"]


def test_failed_callback_can_retry():
    """处理失败时不记录事件，下一次可以重试。"""

    processor = MockCallbackProcessor()
    attempts = []

    def failing_handler():
        attempts.append("attempt")
        raise RuntimeError("temporary failure")

    assert processor.process(
        "event-002",
        failing_handler,
    ) == "retry"

    assert processor.process(
        "event-002",
        lambda: attempts.append("success"),
    ) == "processed"

    assert attempts == ["attempt", "success"]


def test_database_callback_is_persistent_and_idempotent():
    """成功事件写入数据库，重复事件不会再次处理。"""

    processor = DatabaseCallbackProcessor(SessionLocal)
    calls = []

    result = processor.process(
        provider="wecom",
        external_event_id="db-event-001",
        event_type="user_auth",
        handler=lambda: calls.append("handled"),
    )

    duplicate_result = processor.process(
        provider="wecom",
        external_event_id="db-event-001",
        event_type="user_auth",
        handler=lambda: calls.append("duplicate"),
    )

    with SessionLocal() as db:
        event = db.scalar(
            select(IntegrationEvent).where(
                IntegrationEvent.external_event_id == "db-event-001"
            )
        )

    assert result == "processed"
    assert duplicate_result == "duplicate"
    assert calls == ["handled"]
    assert event.status == "processed"
    assert event.retry_count == 1


def test_database_callback_failure_can_retry():
    """数据库记录失败事件后，下一次调用可以重试。"""

    processor = DatabaseCallbackProcessor(SessionLocal)

    assert processor.process(
        provider="wecom",
        external_event_id="db-event-002",
        event_type="user_auth",
        handler=lambda: (_ for _ in ()).throw(
            RuntimeError("temporary failure")
        ),
    ) == "retry"

    assert processor.process(
        provider="wecom",
        external_event_id="db-event-002",
        event_type="user_auth",
        handler=lambda: None,
    ) == "processed"

    with SessionLocal() as db:
        event = db.scalar(
            select(IntegrationEvent).where(
                IntegrationEvent.external_event_id == "db-event-002"
            )
        )

    assert event.status == "processed"
    assert event.retry_count == 2
    assert event.last_error is None


def _signed_callback_request(payload: dict, token: str):
    """构造与 HTTP 请求原文一致的 Mock 签名。"""

    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    timestamp = "1700000000"
    nonce = "http-test-nonce"
    signature = build_mock_signature(token, timestamp, nonce, body)
    headers = {
        "Content-Type": "application/json",
        "X-Mock-Timestamp": timestamp,
        "X-Mock-Nonce": nonce,
        "X-Mock-Signature": signature,
    }
    return body, headers


def test_mock_callback_api_processes_duplicate_once(monkeypatch):
    """HTTP 回调首次处理成功，重复事件不再次处理。"""

    token = "local-callback-token"
    monkeypatch.setenv("WECOM_MODE", "mock")
    monkeypatch.setenv("WECOM_CALLBACK_TOKEN", token)
    payload = {
        "event_id": "http-event-001",
        "event_type": "user_auth",
        "userid": "http-user-001",
        "username": "http_sales",
        "name": "HTTP 演示销售",
    }
    body, headers = _signed_callback_request(payload, token)

    first_response = client.post(
        "/wecom/mock/callback",
        content=body,
        headers=headers,
    )
    duplicate_response = client.post(
        "/wecom/mock/callback",
        content=body,
        headers=headers,
    )

    assert first_response.status_code == 200
    assert first_response.json()["status"] == "processed"
    assert duplicate_response.status_code == 200
    assert duplicate_response.json()["status"] == "duplicate"

    with SessionLocal() as db:
        logs = db.scalars(
            select(AuditLog)
            .where(
                AuditLog.target_type == "integration_event",
                AuditLog.target_id == "http-event-001",
            )
            .order_by(AuditLog.id)
        ).all()

    assert [log.result for log in logs] == ["success", "duplicate"]
    assert all(log.actor_source == "wecom_callback" for log in logs)
    assert all(log.action == "wecom.user_auth.sync" for log in logs)


def test_mock_callback_api_rejects_invalid_signature(monkeypatch):
    """签名不正确时，不进入数据库事件处理。"""

    monkeypatch.setenv("WECOM_MODE", "mock")
    monkeypatch.setenv("WECOM_CALLBACK_TOKEN", "local-callback-token")

    response = client.post(
        "/wecom/mock/callback",
        json={
            "event_id": "http-event-002",
            "event_type": "user_auth",
            "userid": "http-user-002",
            "username": "http_sales_2",
            "name": "签名测试用户",
        },
        headers={
            "X-Mock-Timestamp": "1700000000",
            "X-Mock-Nonce": "http-test-nonce",
            "X-Mock-Signature": "invalid-signature",
        },
    )

    assert response.status_code == 401

    with SessionLocal() as db:
        event = db.scalar(
            select(IntegrationEvent).where(
                IntegrationEvent.external_event_id == "http-event-002"
            )
        )
        audit_log = db.scalar(
            select(AuditLog).where(
                AuditLog.target_id == "http-event-002"
            )
        )

    assert event is None
    assert audit_log is not None
    assert audit_log.action == "wecom.callback.verify"
    assert audit_log.result == "failure"
    assert audit_log.detail_json["reason"] == "invalid_signature"


def test_mock_callback_api_records_missing_signature(monkeypatch):
    """缺少签名请求头时返回 400，并记录安全审计。"""

    monkeypatch.setenv("WECOM_MODE", "mock")
    monkeypatch.setenv("WECOM_CALLBACK_TOKEN", "local-callback-token")

    response = client.post(
        "/wecom/mock/callback",
        json={
            "event_id": "http-event-missing-signature",
            "event_type": "user_auth",
            "userid": "http-user-missing-signature",
            "username": "missing_signature_user",
            "name": "缺少签名用户",
        },
    )

    assert response.status_code == 400

    with SessionLocal() as db:
        audit_log = db.scalar(
            select(AuditLog).where(
                AuditLog.target_id == "http-event-missing-signature"
            )
        )

    assert audit_log is not None
    assert audit_log.action == "wecom.callback.verify"
    assert audit_log.result == "failure"
    assert audit_log.detail_json["reason"] == "missing_signature_headers"


def test_mock_callback_api_rejects_unknown_event_type(monkeypatch):
    """未知事件类型不会进入数据库处理。"""

    token = "local-callback-token"
    monkeypatch.setenv("WECOM_MODE", "mock")
    monkeypatch.setenv("WECOM_CALLBACK_TOKEN", token)
    payload = {
        "event_id": "http-event-unknown",
        "event_type": "unknown_event",
        "userid": "http-user-003",
        "username": "http_sales_3",
        "name": "未知事件用户",
    }
    body, headers = _signed_callback_request(payload, token)

    response = client.post(
        "/wecom/mock/callback",
        content=body,
        headers=headers,
    )

    assert response.status_code == 400

    with SessionLocal() as db:
        event = db.scalar(
            select(IntegrationEvent).where(
                IntegrationEvent.external_event_id
                == "http-event-unknown"
            )
        )

    assert event is None


def test_mock_callback_api_syncs_user_profile(monkeypatch):
    """user_auth 回调会按 userid 创建用户，并同步名称变化。"""

    token = "local-callback-token"
    monkeypatch.setenv("WECOM_MODE", "mock")
    monkeypatch.setenv("WECOM_CALLBACK_TOKEN", token)
    first_payload = {
        "event_id": "http-event-user-001",
        "event_type": "user_auth",
        "userid": "http-user-004",
        "username": "synced_sales",
        "name": "首次名称",
    }
    first_body, first_headers = _signed_callback_request(
        first_payload,
        token,
    )

    first_response = client.post(
        "/wecom/mock/callback",
        content=first_body,
        headers=first_headers,
    )

    assert first_response.status_code == 200
    assert first_response.json()["status"] == "processed"

    with SessionLocal() as db:
        user = db.scalar(
            select(User).where(User.wecom_userid == "http-user-004")
        )
        assert user is not None
        assert user.username == "synced_sales"
        assert user.role == "sales"
        assert user.organization_id is None
        assert user.full_name == "首次名称"

    second_payload = {
        **first_payload,
        "event_id": "http-event-user-002",
        "name": "更新后的名称",
    }
    second_body, second_headers = _signed_callback_request(
        second_payload,
        token,
    )

    second_response = client.post(
        "/wecom/mock/callback",
        content=second_body,
        headers=second_headers,
    )

    assert second_response.status_code == 200
    assert second_response.json()["status"] == "processed"

    with SessionLocal() as db:
        user = db.scalar(
            select(User).where(User.wecom_userid == "http-user-004")
        )
        assert user is not None
        assert user.username == "synced_sales"
        assert user.full_name == "更新后的名称"


def test_mock_callback_api_returns_503_when_user_sync_fails(monkeypatch):
    """用户同步失败时返回 503，并保留 failed 事件状态。"""

    token = "local-callback-token"
    monkeypatch.setenv("WECOM_MODE", "mock")
    monkeypatch.setenv("WECOM_CALLBACK_TOKEN", token)

    register_response = client.post(
        "/auth/register",
        json={
            "username": "conflict_sales",
            "password": "Test123!",
        },
    )
    assert register_response.status_code == 201

    payload = {
        "event_id": "http-event-conflict",
        "event_type": "user_auth",
        "userid": "http-user-conflict",
        "username": "conflict_sales",
        "name": "冲突用户",
    }
    body, headers = _signed_callback_request(payload, token)

    response = client.post(
        "/wecom/mock/callback",
        content=body,
        headers=headers,
    )

    assert response.status_code == 503

    with SessionLocal() as db:
        event = db.scalar(
            select(IntegrationEvent).where(
                IntegrationEvent.external_event_id
                == "http-event-conflict"
            )
        )
        audit_log = db.scalar(
            select(AuditLog).where(
                AuditLog.target_id == "http-event-conflict"
            )
        )

    assert event is not None
    assert event.status == "failed"
    assert audit_log is not None
    assert audit_log.result == "failure"
    assert audit_log.actor_source == "wecom_callback"


def test_mock_callback_processes_chat_message_and_is_idempotent(monkeypatch):
    """聊天回调应写入消息、时间线和加密的 integration payload。"""

    token = "local-callback-token"
    monkeypatch.setenv("WECOM_MODE", "mock")
    monkeypatch.setenv("WECOM_CALLBACK_TOKEN", token)

    with SessionLocal() as db:
        user = User(
            username="callback_chat_sales",
            full_name="回调聊天销售",
            wecom_userid="callback-chat-user",
            hashed_password=hash_password("unused-password"),
        )
        db.add(user)
        db.flush()
        customer = Customer(
            owner_id=user.id,
            name="回调聊天客户",
            phone="13700000000",
        )
        db.add(customer)
        db.commit()
        customer_id = customer.id

    payload = {
        "event_id": "http-event-chat-001",
        "event_type": "chat_message",
        "userid": "callback-chat-user",
        "customer_id": customer_id,
        "wecom_message_id": "callback-msg-001",
        "direction": "inbound",
        "message_type": "text",
        "content": "家长咨询数学课程 13800138000",
    }
    body, headers = _signed_callback_request(payload, token)

    first_response = client.post(
        "/wecom/mock/callback",
        content=body,
        headers=headers,
    )
    duplicate_response = client.post(
        "/wecom/mock/callback",
        content=body,
        headers=headers,
    )

    assert first_response.status_code == 200
    assert first_response.json()["status"] == "processed"
    assert duplicate_response.status_code == 200
    assert duplicate_response.json()["status"] == "duplicate"

    with SessionLocal() as db:
        message = db.scalar(
            select(ChatMessage).where(
                ChatMessage.wecom_message_id == "callback-msg-001"
            )
        )
        event = db.scalar(
            select(IntegrationEvent).where(
                IntegrationEvent.external_event_id
                == "http-event-chat-001"
            )
        )
        timeline = db.scalar(
            select(TimelineEvent).where(
                TimelineEvent.event_type == "wecom_message",
                TimelineEvent.customer_id == customer_id,
            )
        )

    assert message is not None
    assert message.content_encrypted != payload["content"]
    assert event is not None
    assert event.payload_encrypted is not None
    assert body not in event.payload_encrypted
    assert timeline is not None


def test_mock_callback_does_not_overwrite_existing_permissions(monkeypatch):
    """同步已有用户资料时，不改变本地角色和组织。"""

    token = "local-callback-token"
    monkeypatch.setenv("WECOM_MODE", "mock")
    monkeypatch.setenv("WECOM_CALLBACK_TOKEN", token)

    register_response = client.post(
        "/auth/register",
        json={
            "username": "existing_manager",
            "password": "Test123!",
        },
    )
    assert register_response.status_code == 201

    with SessionLocal() as db:
        organization = Organization(
            name="回调测试组织",
            type="team",
        )
        db.add(organization)
        db.flush()
        organization_id = organization.id

        user = db.scalar(
            select(User).where(User.username == "existing_manager")
        )
        assert user is not None
        user.role = "manager"
        user.organization_id = organization_id
        user.wecom_userid = "http-user-manager"
        db.commit()

    payload = {
        "event_id": "http-event-manager",
        "event_type": "user_auth",
        "userid": "http-user-manager",
        "username": "renamed_manager",
        "name": "更新后的经理名称",
    }
    body, headers = _signed_callback_request(payload, token)

    response = client.post(
        "/wecom/mock/callback",
        content=body,
        headers=headers,
    )

    assert response.status_code == 200

    with SessionLocal() as db:
        user = db.scalar(
            select(User).where(User.wecom_userid == "http-user-manager")
        )
        assert user is not None
        assert user.username == "existing_manager"
        assert user.role == "manager"
        assert user.organization_id == organization_id
        assert user.full_name == "更新后的经理名称"
