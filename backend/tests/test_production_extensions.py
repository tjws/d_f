import uuid
from datetime import datetime, timedelta, timezone

import pytest

from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.db.session import SessionLocal
from app.main import app
from app.models.ai_suggestion_feedback import AISuggestionFeedback
from app.models.audit_log import AuditLog
from app.models.chat_message import ChatMessage
from app.models.course_order import CourseOrder
from app.models.customer import Customer
from app.models.service_ticket import ServiceTicket
from app.models.timeline_event import TimelineEvent
from app.models.user import User


client = TestClient(app)


def setup_function():
    with SessionLocal() as db:
        for model in (AISuggestionFeedback, ChatMessage, ServiceTicket, CourseOrder, TimelineEvent, AuditLog, Customer, User):
            db.execute(delete(model))
        db.commit()


def _login(role: str = "admin") -> dict[str, str]:
    username = f"extension_{uuid.uuid4().hex[:8]}"
    assert client.post("/auth/register", json={"username": username, "password": "Test123!"}).status_code == 201
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.username == username))
        assert user is not None
        user.role = role
        db.commit()
    token = client.post("/auth/token", data={"username": username, "password": "Test123!"}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _customer(headers: dict[str, str]) -> int:
    return client.post("/customers", headers=headers, json={"name": "治理扩展客户", "phone": "13800138000"}).json()["id"]


def test_voice_message_mock_transcription_is_idempotent():
    headers = _login("admin")
    customer_id = _customer(headers)
    created = client.post(f"/customers/{customer_id}/chat-messages/mock", headers=headers, json={"wecom_message_id": "voice-001", "direction": "inbound", "message_type": "voice", "media_object_key": "mock-voice:家长想了解数学课程"})
    assert created.status_code == 201
    message_id = created.json()["id"]
    first = client.post(f"/customers/{customer_id}/chat-messages/{message_id}/transcribe", headers=headers)
    assert first.status_code == 200
    assert first.json()["content"] == "家长想了解数学课程"
    second = client.post(f"/customers/{customer_id}/chat-messages/{message_id}/transcribe", headers=headers)
    assert second.status_code == 200
    with SessionLocal() as db:
        events = list(db.scalars(select(TimelineEvent).where(TimelineEvent.event_type == "voice_transcribed")).all())
        assert len(events) == 1


def test_retention_defaults_to_preview_only(monkeypatch):
    headers = _login("admin")
    monkeypatch.delenv("DATA_RETENTION_AUTO_DELETE", raising=False)
    policy = client.get("/admin/data-retention", headers=headers)
    assert policy.status_code == 200
    assert policy.json()["automatic_deletion_enabled"] is False
    preview = client.post("/admin/data-retention/preview", headers=headers, json={"dataset": "chat_messages"})
    assert preview.status_code == 200
    denied = client.post("/admin/data-retention/purge", headers=headers, json={"dataset": "chat_messages", "confirm": True})
    assert denied.status_code == 409


def test_mock_operations_sync_is_idempotent_and_role_protected():
    headers = _login("admin")
    customer_id = _customer(headers)
    payload = {"customer_id": customer_id, "orders": [{"external_order_id": "sync-order-1", "course_name": "同步课程", "amount": "100.00"}], "tickets": [{"external_ticket_id": "sync-ticket-1", "summary": "同步工单"}]}
    first = client.post("/admin/operations/mock-sync", headers=headers, json=payload)
    assert first.status_code == 200
    assert first.json()["orders_created"] == 1
    second = client.post("/admin/operations/mock-sync", headers=headers, json=payload)
    assert second.status_code == 200
    assert second.json()["orders_skipped"] == 1
    assert second.json()["tickets_skipped"] == 1
    sales = _login("sales")
    assert client.post("/admin/operations/mock-sync", headers=sales, json=payload).status_code == 403


def test_backup_status_reads_latest_file_only(monkeypatch, tmp_path):
    import app.services.system_status_service as service

    backup = tmp_path / "latest.dump"
    backup.write_bytes(b"backup")
    monkeypatch.setenv("BACKUP_DIRECTORY", str(tmp_path))
    monkeypatch.setenv("BACKUP_MAX_AGE_HOURS", "24")
    status = service.get_backup_status()
    assert status["status"] == "ok"
    assert status["latest_backup_name"] == "latest.dump"


def test_backup_job_verifies_and_guards_prune(monkeypatch, tmp_path):
    import scripts.backup_job as backup_job

    backup = tmp_path / "created.dump"
    backup.write_bytes(b"backup")
    verified: list[str] = []
    monkeypatch.setattr(backup_job, "create_backup", lambda output: backup)
    monkeypatch.setattr(backup_job, "verify_backup", lambda path: verified.append(str(path)))
    assert backup_job.run_job(tmp_path) == backup
    assert verified == [str(backup)]
    monkeypatch.delenv("BACKUP_PRUNE_ENABLED", raising=False)
    with pytest.raises(ValueError):
        backup_job.run_job(tmp_path, prune_days=30, confirm_prune=True)
