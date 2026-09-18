"""覆盖本地 Mock 工作台主路径的端到端 API 验收。"""

import base64

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.db.session import SessionLocal
from app.main import app
from app.models.ai_suggestion import AISuggestion
from app.models.ai_suggestion_feedback import AISuggestionFeedback
from app.models.ai_workflow_run import AIWorkflowRun
from app.models.audit_log import AuditLog
from app.models.chat_message import ChatMessage
from app.models.customer import Customer
from app.models.customer_profile import CustomerProfile
from app.models.customer_tag import CustomerTag
from app.models.customer_transfer import CustomerTransfer
from app.models.integration_event import IntegrationEvent
from app.models.organization import Organization
from app.models.schedule import Schedule
from app.models.student import Student
from app.models.tag import Tag
from app.models.timeline_event import TimelineEvent
from app.models.user import User


client = TestClient(app)


@pytest.fixture(autouse=True)
def encryption_key(monkeypatch):
    monkeypatch.setenv("APP_ENCRYPTION_KEY", base64.urlsafe_b64encode(b"e" * 32).decode("ascii"))


def setup_function():
    with SessionLocal() as db:
        for model in (AISuggestionFeedback, AIWorkflowRun, Schedule, CustomerTag, Tag, AISuggestion, CustomerProfile, CustomerTransfer, ChatMessage, TimelineEvent, IntegrationEvent, AuditLog, Student, Customer, Organization, User):
            db.execute(delete(model))
        db.commit()


def test_mock_workspace_end_to_end_flow():
    registered = client.post("/auth/register", json={"username": "e2e_admin", "password": "Test123!", "full_name": "验收管理员"})
    assert registered.status_code == 201
    with SessionLocal() as db:
        user = db.query(User).filter_by(username="e2e_admin").one()
        user.role = "admin"
        db.commit()
    login = client.post("/auth/token", data={"username": "e2e_admin", "password": "Test123!"})
    assert login.status_code == 200
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    customer = client.post("/customers", headers=headers, json={"name": "端到端家长", "phone": "13800998877", "interested_subject": "数学"})
    assert customer.status_code == 201
    customer_id = customer.json()["id"]

    student = client.post(f"/customers/{customer_id}/students", headers=headers, json={"name": "端到端学生", "grade": "初一", "school": "演示中学"})
    assert student.status_code == 201
    inbound = client.post(f"/customers/{customer_id}/chat-messages/mock", headers=headers, json={"wecom_message_id": "e2e-parent-001", "direction": "inbound", "message_type": "text", "content": "想了解初一数学试听课和收费"})
    assert inbound.status_code == 201

    profile = client.post(f"/customers/{customer_id}/profiles/draft", headers=headers)
    assert profile.status_code == 201
    confirmed = client.post(f"/customers/{customer_id}/profiles/{profile.json()['id']}/confirm", headers=headers)
    assert confirmed.status_code == 200

    workflow = client.post(f"/customers/{customer_id}/ai-workflow", headers=headers, json={"goal": "reply"})
    assert workflow.status_code == 200
    assert workflow.json()["status"] == "waiting_human"
    suggestion_id = workflow.json()["suggestion_ids"][0]
    suggestion = client.get(f"/customers/{customer_id}/suggestions", headers=headers).json()[0]
    assert suggestion["id"] == suggestion_id
    assert any(item["source_type"] == "knowledge" for item in suggestion["evidence"])

    edited = client.patch(f"/customers/{customer_id}/suggestions/{suggestion_id}", headers=headers, json={"content": {"text": "人工确认后的试听回复"}})
    assert edited.status_code == 200
    accepted = client.post(f"/customers/{customer_id}/suggestions/{suggestion_id}/accept", headers=headers)
    assert accepted.status_code == 200

    outbound = client.post(
        f"/customers/{customer_id}/chat-messages/mock",
        headers=headers,
        json={
            "wecom_message_id": "e2e-sales-001",
            "suggestion_id": suggestion_id,
            "direction": "outbound",
            "message_type": "text",
            "content": "人工确认后的试听回复",
        },
    )
    assert outbound.status_code == 201
    assert outbound.json()["suggestion_id"] == suggestion_id
    feedback = client.get(f"/customers/{customer_id}/suggestions/{suggestion_id}/feedback", headers=headers)
    assert feedback.status_code == 200
    assert feedback.json()["action"] == "accepted"
    messages = client.get(f"/customers/{customer_id}/chat-messages", headers=headers)
    timeline = client.get(f"/customers/{customer_id}/timeline-events", headers=headers)
    assert messages.status_code == timeline.status_code == 200
    assert len(messages.json()) == 2
    assert len(timeline.json()) == 2

    dashboard = client.get("/admin/ai-dashboard", headers=headers)
    assert dashboard.status_code == 200
    # 本流程确认了画像草稿和回复建议两条 AI 建议。
    assert dashboard.json()["accepted"] == 2
    assert dashboard.json()["adoption_rate"] == 1

    sales_register = client.post("/auth/register", json={"username": "e2e_sales", "password": "Test123!"})
    assert sales_register.status_code == 201
    sales_login = client.post("/auth/token", data={"username": "e2e_sales", "password": "Test123!"})
    denied = client.get("/admin/ai-dashboard", headers={"Authorization": f"Bearer {sales_login.json()['access_token']}"})
    assert denied.status_code == 403
