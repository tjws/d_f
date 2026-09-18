import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.db.session import SessionLocal
from app.main import app
from app.models.ai_suggestion import AISuggestion
from app.models.ai_suggestion_feedback import AISuggestionFeedback
from app.models.ai_workflow_run import AIWorkflowRun
from app.models.audit_log import AuditLog
from app.models.customer import Customer
from app.models.customer_profile import CustomerProfile
from app.models.customer_tag import CustomerTag
from app.models.schedule import Schedule
from app.models.student import Student
from app.models.tag import Tag
from app.models.timeline_event import TimelineEvent
from app.models.user import User
from scripts.backup_postgres import main as backup_main
from scripts.restore_postgres import main as restore_main
from scripts.verify_backup import main as verify_backup_main


client = TestClient(app)


def setup_function():
    with SessionLocal() as db:
        db.execute(delete(AISuggestionFeedback))
        db.execute(delete(AIWorkflowRun))
        db.execute(delete(Schedule))
        db.execute(delete(CustomerTag))
        db.execute(delete(Tag))
        db.execute(delete(AISuggestion))
        db.execute(delete(CustomerProfile))
        db.execute(delete(TimelineEvent))
        db.execute(delete(AuditLog))
        db.execute(delete(Student))
        db.execute(delete(Customer))
        db.execute(delete(User))
        db.commit()


def _admin_headers() -> tuple[dict[str, str], int, int]:
    response = client.post("/auth/register", json={"username": "dashboard_admin", "password": "Test123!"})
    assert response.status_code == 201
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.username == "dashboard_admin"))
        user.role = "admin"
        customer = Customer(name="看板客户", phone="13800000001", owner_id=user.id)
        db.add(customer)
        db.flush()
        suggestion = AISuggestion(customer_id=customer.id, user_id=user.id, suggestion_type="reply", content_json={"text": "建议"}, evidence_json=[], status="accepted", model_name="mock", model_version="1", prompt_version="test")
        db.add(suggestion)
        db.flush()
        db.add(AISuggestionFeedback(suggestion_id=suggestion.id, customer_id=customer.id, target_type="reply", target_id=str(suggestion.id), actor_user_id=user.id, action="accepted", created_at=datetime.now(timezone.utc)))
        db.commit()
        user_id, customer_id = user.id, customer.id
    login = client.post("/auth/token", data={"username": "dashboard_admin", "password": "Test123!"})
    return {"Authorization": f"Bearer {login.json()['access_token']}"}, user_id, customer_id


def test_request_id_is_echoed_and_readiness_checks_dependencies(monkeypatch):
    class FakeRedis:
        def ping(self):
            return True

        def close(self):
            return None

    import app.main as main_module
    monkeypatch.setattr(main_module.redis.Redis, "from_url", lambda *args, **kwargs: FakeRedis())
    response = client.get("/health/ready", headers={"X-Request-ID": "governance-test"})
    assert response.status_code == 200
    assert response.json()["status"] == "ready"
    assert response.headers["X-Request-ID"] == "governance-test"


def test_ai_dashboard_is_admin_only_and_returns_adoption_metrics():
    headers, _, _ = _admin_headers()
    response = client.get("/admin/ai-dashboard", headers=headers)
    assert response.status_code == 200
    payload = response.json()
    assert payload["suggestions_total"] == 1
    assert payload["accepted"] == 1
    assert payload["adoption_rate"] == 1

    sales = client.post("/auth/register", json={"username": "dashboard_sales", "password": "Test123!"})
    login = client.post("/auth/token", data={"username": "dashboard_sales", "password": "Test123!"})
    denied = client.get("/admin/ai-dashboard", headers={"Authorization": f"Bearer {login.json()['access_token']}"})
    assert denied.status_code == 403


def test_accept_endpoint_records_feedback_and_is_queryable():
    response = client.post("/auth/register", json={"username": "feedback_owner", "password": "Test123!"})
    assert response.status_code == 201
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.username == "feedback_owner"))
        customer = Customer(name="反馈客户", phone="13800000002", owner_id=user.id)
        db.add(customer)
        db.flush()
        suggestion = AISuggestion(customer_id=customer.id, user_id=user.id, suggestion_type="reply", content_json={"text": "请人工确认"}, evidence_json=[], status="draft", model_name="mock", model_version="1", prompt_version="test")
        db.add(suggestion)
        db.commit()
        customer_id, suggestion_id = customer.id, suggestion.id
    login = client.post("/auth/token", data={"username": "feedback_owner", "password": "Test123!"})
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    accepted = client.post(f"/customers/{customer_id}/suggestions/{suggestion_id}/accept", headers=headers)
    assert accepted.status_code == 200
    feedback = client.get(f"/customers/{customer_id}/suggestions/{suggestion_id}/feedback", headers=headers)
    assert feedback.status_code == 200
    assert feedback.json()["action"] == "accepted"


def test_backup_and_restore_scripts_require_postgres_and_explicit_confirmation(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///local.db")
    monkeypatch.setattr(sys, "argv", ["backup_postgres.py"])
    with pytest.raises(SystemExit):
        backup_main()
    calls = []
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@localhost/db")
    monkeypatch.setattr("scripts.backup_postgres.subprocess.run", lambda command, check: calls.append(command))
    monkeypatch.setattr(sys, "argv", ["backup_postgres.py", "--output", str(tmp_path)])
    assert backup_main() == 0
    assert calls and calls[0][0:3] == ["pg_dump", "--format=custom", "--no-owner"]
    backup = tmp_path / "sample.dump"
    backup.write_bytes(b"placeholder")
    monkeypatch.setenv("RESTORE_DATABASE_URL", "postgresql+psycopg://u:p@localhost/db")
    with pytest.raises(SystemExit):
        monkeypatch.setattr(sys, "argv", ["restore_postgres.py", str(backup)])
        restore_main()


def test_backup_verification_is_read_only_and_requires_existing_file(monkeypatch, tmp_path: Path, capsys):
    missing = tmp_path / "missing.dump"
    monkeypatch.setattr(sys, "argv", ["verify_backup.py", str(missing)])
    with pytest.raises(SystemExit):
        verify_backup_main()

    backup = tmp_path / "sample.dump"
    backup.write_bytes(b"placeholder")
    calls = []
    monkeypatch.setattr("scripts.verify_backup.subprocess.run", lambda command, check: calls.append(command))
    monkeypatch.setattr(sys, "argv", ["verify_backup.py", str(backup)])
    assert verify_backup_main() == 0
    assert calls == [["pg_restore", "--list", "--file", "-", str(backup)]]
    assert "backup_verified=" in capsys.readouterr().out
