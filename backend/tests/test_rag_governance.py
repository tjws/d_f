import base64

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.db.session import SessionLocal
from app.main import app
from app.models.ai_rag_interaction import AIRagInteraction
from app.models.ai_suggestion import AISuggestion
from app.models.ai_suggestion_feedback import AISuggestionFeedback
from app.models.ai_workflow_run import AIWorkflowRun
from app.models.ai_rollout_daily_report import AIRolloutDailyReport
from app.models.ai_rollout_membership import AIRolloutMembership
from app.models.audit_log import AuditLog
from app.models.chat_message import ChatMessage
from app.models.customer import Customer
from app.models.customer_profile import CustomerProfile
from app.models.customer_tag import CustomerTag
from app.models.rag_evaluation_case import RAGEvaluationCase
from app.models.schedule import Schedule
from app.models.system_setting import SystemSetting
from app.models.user import User


client = TestClient(app)


@pytest.fixture(autouse=True)
def encryption_key(monkeypatch):
    monkeypatch.setenv("APP_ENCRYPTION_KEY", base64.urlsafe_b64encode(b"g" * 32).decode("ascii"))
    monkeypatch.setenv("AI_PROVIDER", "mock")
    monkeypatch.setenv("AI_AGENT_PLANNER_PROVIDER", "mock")


def setup_function():
    with SessionLocal() as db:
        db.execute(delete(AIRolloutDailyReport))
        db.execute(delete(AIRolloutMembership))
        db.execute(delete(RAGEvaluationCase))
        db.execute(delete(AIRagInteraction))
        db.execute(delete(AISuggestionFeedback))
        db.execute(delete(AIWorkflowRun))
        db.execute(delete(ChatMessage))
        db.execute(delete(Schedule))
        db.execute(delete(CustomerTag))
        db.execute(delete(AISuggestion))
        db.execute(delete(CustomerProfile))
        db.execute(delete(AuditLog))
        db.execute(delete(SystemSetting))
        db.execute(delete(Customer))
        db.execute(delete(User))
        db.commit()


def _auth(username: str = "governance_admin") -> tuple[dict[str, str], int]:
    registered = client.post("/auth/register", json={"username": username, "password": "Test123!"})
    assert registered.status_code == 201
    with SessionLocal() as db:
        user = db.get(User, registered.json()["id"])
        assert user is not None
        user.role = "admin"
        db.commit()
    login = client.post("/auth/token", data={"username": username, "password": "Test123!"})
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}, registered.json()["id"]


def _customer(headers: dict[str, str]) -> int:
    response = client.post("/customers", headers=headers, json={"name": "治理测试家长", "phone": "13800138000"})
    assert response.status_code == 201
    return response.json()["id"]


def test_comprehensive_feedback_is_idempotent_and_rag_is_measured():
    headers, _ = _auth()
    customer_id = _customer(headers)
    inbound = client.post(
        f"/customers/{customer_id}/chat-messages/mock",
        headers=headers,
        json={"wecom_message_id": "governance-msg-1", "direction": "inbound", "content": "课程价格是多少"},
    )
    assert inbound.status_code == 201

    run = client.post(f"/customers/{customer_id}/agent/run", headers=headers, json={"task": "comprehensive"})
    assert run.status_code == 200
    run_id = run.json()["workflow"]["run_id"]
    feedback_payload = {"action": "missing_information", "note": "请补充可验证的班型信息"}
    first = client.post(f"/customers/{customer_id}/agent/runs/{run_id}/feedback", headers=headers, json=feedback_payload)
    second = client.post(f"/customers/{customer_id}/agent/runs/{run_id}/feedback", headers=headers, json=feedback_payload)
    assert first.status_code == second.status_code == 200
    assert first.json()["id"] == second.json()["id"]

    with SessionLocal() as db:
        assert db.scalar(select(AISuggestionFeedback).where(AISuggestionFeedback.target_type == "agent_run")).id == first.json()["id"]
        assert db.scalar(select(AIRagInteraction).where(AIRagInteraction.run_id == run_id)) is not None
        assert db.scalar(select(RAGEvaluationCase).where(RAGEvaluationCase.source_type == "agent_feedback")) is not None

    dashboard = client.get("/admin/ai-dashboard", headers=headers)
    assert dashboard.status_code == 200
    assert dashboard.json()["agent_feedback_total"] == 1
    assert dashboard.json()["rag_queries_total"] >= 1

    cases = client.get("/knowledge/admin/evaluation-cases", headers=headers)
    assert cases.status_code == 200
    assert len(cases.json()) == 1
    case_id = cases.json()[0]["id"]
    reviewed = client.patch(
        f"/knowledge/admin/evaluation-cases/{case_id}",
        headers=headers,
        json={"status": "reviewed", "expected_document_ids": ["03_pricing_faq"], "review_note": "补充价格资料"},
    )
    assert reviewed.status_code == 200
    assert reviewed.json()["status"] == "reviewed"
    report = client.get("/knowledge/admin/evaluation-report", headers=headers)
    assert report.status_code == 200
    assert report.json()["queue"]["reviewed"] == 1


def test_sales_cannot_review_rag_evaluation_cases():
    admin_headers, _ = _auth("evaluation_owner")
    customer_id = _customer(admin_headers)
    with SessionLocal() as db:
        from app.services.ai_rag_telemetry_service import record_rag_interaction

        record_rag_interaction(
            db,
            customer_id=customer_id,
            actor_user_id=None,
            run_id=None,
            suggestion_id=None,
            entrypoint="manual_search",
            query="未知问题",
            retrieval_mode="keyword",
            matched=False,
            fallback=True,
        )
        db.commit()
        case_id = db.scalar(select(RAGEvaluationCase)).id
    registered = client.post("/auth/register", json={"username": "evaluation_sales", "password": "Test123!"})
    assert registered.status_code == 201
    token = client.post("/auth/token", data={"username": "evaluation_sales", "password": "Test123!"}).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    response = client.patch(
        f"/knowledge/admin/evaluation-cases/{case_id}",
        headers=headers,
        json={"status": "reviewed", "expected_document_ids": []},
    )
    assert response.status_code == 403


def test_comprehensive_agent_kill_switch_falls_back_to_reply_workflow():
    headers, _ = _auth("kill_switch_admin")
    customer_id = _customer(headers)
    changed = client.put(
        "/admin/system-settings/comprehensive_agent_enabled",
        headers=headers,
        json={"value": False},
    )
    assert changed.status_code == 200
    assert changed.json()["value"] is False

    response = client.post(
        f"/customers/{customer_id}/agent/run",
        headers=headers,
        json={"task": "comprehensive"},
    )
    assert response.status_code == 200
    assert response.json()["intent"] == "reply"
    assert response.json()["metadata"]["reason"] == "global_kill_switch"
    assert response.json()["human_confirmation_required"] is True


def test_ai_rollout_pilot_gate_membership_and_daily_report():
    headers, admin_id = _auth("rollout_admin")
    customer_id = _customer(headers)

    switched = client.put(
        "/admin/ai-rollout/config",
        headers=headers,
        json={"mode": "pilot"},
    )
    assert switched.status_code == 200
    assert switched.json()["mode"] == "pilot"

    blocked = client.post(
        f"/customers/{customer_id}/agent/run",
        headers=headers,
        json={"task": "comprehensive"},
    )
    assert blocked.status_code == 403
    assert "灰度名单" in blocked.json()["detail"]

    added = client.post(
        "/admin/ai-rollout/members",
        headers=headers,
        json={"user_id": admin_id, "segment": "experienced"},
    )
    assert added.status_code == 201
    assert added.json()["status"] == "active"

    allowed = client.post(
        f"/customers/{customer_id}/agent/run",
        headers=headers,
        json={"task": "comprehensive"},
    )
    assert allowed.status_code == 200
    assert allowed.json()["human_confirmation_required"] is True

    report = client.post("/admin/ai-rollout/reports/generate", headers=headers)
    assert report.status_code == 200
    assert report.json()["metrics"]["active_member_count"] == 1
    listed = client.get("/admin/ai-rollout/reports", headers=headers)
    assert listed.status_code == 200
    assert listed.json()[0]["id"] == report.json()["id"]
