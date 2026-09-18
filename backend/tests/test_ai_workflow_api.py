import base64

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.db.session import SessionLocal
from app.main import app
from app.models.ai_suggestion import AISuggestion
from app.models.ai_workflow_run import AIWorkflowRun
from app.models.audit_log import AuditLog
from app.models.customer import Customer
from app.models.customer_profile import CustomerProfile
from app.models.customer_tag import CustomerTag
from app.models.organization import Organization
from app.models.schedule import Schedule
from app.models.system_setting import SystemSetting
from app.models.student import Student
from app.models.tag import Tag
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
        db.execute(delete(AIWorkflowRun))
        db.execute(delete(Schedule))
        db.execute(delete(CustomerTag))
        db.execute(delete(Tag))
        db.execute(delete(AISuggestion))
        db.execute(delete(CustomerProfile))
        db.execute(delete(TimelineEvent))
        db.execute(delete(AuditLog))
        # 每个工作流用例独立验证环境变量额度，避免迁移默认设置污染测试边界。
        db.execute(delete(SystemSetting))
        db.execute(delete(Student))
        db.execute(delete(Organization))
        db.execute(delete(Customer))
        db.execute(delete(User))
        db.commit()


def test_ai_workflow_creates_profile_first_then_reply_after_confirmation():
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

    profile_workflow = client.post(
        f"/customers/{customer_id}/ai-workflow",
        headers=headers,
    )
    assert profile_workflow.status_code == 200
    assert profile_workflow.json()["status"] == "waiting_human"
    assert profile_workflow.json()["run_id"] is not None
    assert profile_workflow.json()["next_action"] == "confirm_profile"
    assert profile_workflow.json()["profile_id"] is not None
    assert profile_workflow.json()["suggestion_ids"] == []

    profiles = client.get(f"/customers/{customer_id}/profiles", headers=headers)
    assert profiles.status_code == 200
    draft = profiles.json()[0]
    assert draft["id"] == profile_workflow.json()["profile_id"]
    assert draft["status"] == "draft"

    with SessionLocal() as db:
        workflow_run = db.get(AIWorkflowRun, profile_workflow.json()["run_id"])
        audit_log = db.scalar(
            select(AuditLog).where(
                AuditLog.target_type == "customer_profile",
                AuditLog.target_id == str(draft["id"]),
            )
        )
    assert workflow_run is not None
    assert workflow_run.status == "succeeded"
    assert workflow_run.result_json["next_action"] == "confirm_profile"
    assert audit_log is not None
    assert audit_log.action == "customer.profile_generated"
    assert audit_log.detail_json["workflow"] == "langgraph"

    confirmed = client.post(
        f"/customers/{customer_id}/profiles/{draft['id']}/confirm",
        headers=headers,
    )
    assert confirmed.status_code == 200

    response = client.post(
        f"/customers/{customer_id}/ai-workflow",
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "waiting_human"
    assert response.json()["next_action"] == "review_reply"
    assert response.json()["profile_id"] is None
    assert len(response.json()["suggestion_ids"]) == 1

    suggestions = client.get(
        f"/customers/{customer_id}/suggestions",
        headers=headers,
    )
    assert suggestions.status_code == 200
    assert suggestions.json()[0]["status"] == "draft"

    tag_response = client.post(
        f"/customers/{customer_id}/ai-workflow",
        headers=headers,
        json={"goal": "tag"},
    )
    assert tag_response.status_code == 200
    assert tag_response.json()["next_action"] == "confirm_tags"
    assert len(tag_response.json()["customer_tag_ids"]) == 1
    tags = client.get(f"/customers/{customer_id}/tags", headers=headers)
    assert tags.status_code == 200
    assert tags.json()[0]["status"] == "suggested"
    with SessionLocal() as db:
        tag_audit_log = db.scalar(
            select(AuditLog).where(
                AuditLog.target_type == "customer_tag",
                AuditLog.target_id == str(tags.json()[0]["id"]),
            )
        )
    assert tag_audit_log is not None
    assert tag_audit_log.detail_json["workflow"] == "langgraph"

    schedule_response = client.post(
        f"/customers/{customer_id}/ai-workflow",
        headers=headers,
        json={"goal": "schedule"},
    )
    assert schedule_response.status_code == 200
    assert schedule_response.json()["next_action"] == "review_schedule"
    assert len(schedule_response.json()["suggestion_ids"]) == 1
    schedule_suggestions = client.get(
        f"/customers/{customer_id}/schedule-suggestions",
        headers=headers,
    )
    assert schedule_suggestions.status_code == 200
    assert schedule_suggestions.json()[0]["suggestion_type"] == "schedule"
    with SessionLocal() as db:
        schedule_audit_log = db.scalar(
            select(AuditLog).where(
                AuditLog.target_type == "ai_suggestion",
                AuditLog.target_id == str(schedule_response.json()["suggestion_ids"][0]),
            )
        )
    assert schedule_audit_log is not None
    assert schedule_audit_log.detail_json["workflow"] == "langgraph"

    unauthenticated = client.post(f"/customers/{customer_id}/ai-workflow")
    assert unauthenticated.status_code == 401


def test_ai_workflow_sse_events_respect_auth_and_emit_terminal_state():
    register = client.post(
        "/auth/register",
        json={"username": "sse_owner", "password": "Test123!"},
    )
    assert register.status_code == 201
    login = client.post(
        "/auth/token",
        data={"username": "sse_owner", "password": "Test123!"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    customer = client.post(
        "/customers",
        headers=headers,
        json={"name": "SSE 测试客户", "phone": "13800138009"},
    )
    customer_id = customer.json()["id"]
    run = client.post(f"/customers/{customer_id}/ai-workflow", headers=headers)
    assert run.status_code == 200
    run_id = run.json()["run_id"]

    events = client.get(
        f"/customers/{customer_id}/ai-workflow/{run_id}/events",
        headers=headers,
    )
    assert events.status_code == 200
    assert events.headers["content-type"].startswith("text/event-stream")
    assert "event: workflow" in events.text
    assert "event: done" in events.text
    assert f'"run_id":{run_id}' in events.text

    unauthenticated = client.get(
        f"/customers/{customer_id}/ai-workflow/{run_id}/events",
    )
    assert unauthenticated.status_code == 401


def test_zero_bailian_daily_limit_rejects_before_model_or_queue(monkeypatch):
    """零额度是硬成本边界：创建任务之前就拒绝，不能产生隐式模型调用。"""

    monkeypatch.setenv("AI_PROVIDER", "bailian")
    monkeypatch.setenv("AI_DAILY_BAILIAN_REQUEST_LIMIT", "0")
    register = client.post(
        "/auth/register",
        json={"username": "quota_owner", "password": "Test123!"},
    )
    assert register.status_code == 201
    login = client.post(
        "/auth/token",
        data={"username": "quota_owner", "password": "Test123!"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    customer = client.post(
        "/customers",
        headers=headers,
        json={"name": "额度测试客户", "phone": "13800138000"},
    )

    response = client.post(
        f"/customers/{customer.json()['id']}/ai-workflow",
        headers=headers,
    )

    assert response.status_code == 429
    with SessionLocal() as db:
        assert db.query(AIWorkflowRun).count() == 0


def test_ai_workflow_idempotency_reuses_existing_queue_item(monkeypatch):
    """网络重发同一个幂等键时只保留一条任务，也只投递一次 Worker 消息。"""

    monkeypatch.setenv("AI_WORKFLOW_EXECUTION_MODE", "queue")
    from app.workers import ai_workflow_tasks

    sent: list[int] = []
    monkeypatch.setattr(ai_workflow_tasks.execute_ai_workflow_task, "send", lambda run_id: sent.append(run_id))
    register = client.post("/auth/register", json={"username": "idempotent_owner", "password": "Test123!"})
    assert register.status_code == 201
    login = client.post("/auth/token", data={"username": "idempotent_owner", "password": "Test123!"})
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    customer = client.post("/customers", headers=headers, json={"name": "幂等测试客户", "phone": "13800138001"})
    customer_id = customer.json()["id"]
    payload = {"goal": "reply", "idempotency_key": "reply-idempotency-001"}

    first = client.post(f"/customers/{customer_id}/ai-workflow", headers=headers, json=payload)
    second = client.post(f"/customers/{customer_id}/ai-workflow", headers=headers, json=payload)

    assert first.status_code == second.status_code == 200
    assert first.json()["run_id"] == second.json()["run_id"]
    assert sent == [first.json()["run_id"]]
    with SessionLocal() as db:
        assert db.query(AIWorkflowRun).filter_by(customer_id=customer_id).count() == 1


def test_failed_ai_workflow_requires_explicit_confirmation_to_retry(monkeypatch):
    """失败任务只能由人工确认后重新排队，并受最大尝试次数限制。"""

    monkeypatch.setenv("AI_WORKFLOW_EXECUTION_MODE", "queue")
    from app.workers import ai_workflow_tasks

    sent: list[int] = []
    monkeypatch.setattr(ai_workflow_tasks.execute_ai_workflow_task, "send", lambda run_id: sent.append(run_id))
    register = client.post("/auth/register", json={"username": "retry_owner", "password": "Test123!"})
    assert register.status_code == 201
    login = client.post("/auth/token", data={"username": "retry_owner", "password": "Test123!"})
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    customer = client.post("/customers", headers=headers, json={"name": "重试测试客户", "phone": "13800138002"})
    customer_id = customer.json()["id"]
    with SessionLocal() as db:
        run = AIWorkflowRun(
            customer_id=customer_id,
            actor_user_id=register.json()["id"],
            goal="reply",
            provider_name="mock",
            status="failed",
            attempt_count=1,
            result_json={"status": "failed", "error": "test"},
        )
        db.add(run)
        db.commit()
        db.refresh(run)
        run_id = run.id

    missing_confirmation = client.post(
        f"/customers/{customer_id}/ai-workflow/{run_id}/retry",
        headers=headers,
        json={"confirm": False},
    )
    assert missing_confirmation.status_code == 400
    retried = client.post(
        f"/customers/{customer_id}/ai-workflow/{run_id}/retry",
        headers=headers,
        json={"confirm": True},
    )
    assert retried.status_code == 200
    assert retried.json()["status"] == "queued"
    assert retried.json()["retryable"] is False
    assert retried.json()["attempt_count"] == 1
    assert sent == [run_id]
