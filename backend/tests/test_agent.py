import base64
from datetime import datetime, timezone

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
from app.models.organization import Organization
from app.models.schedule import Schedule
from app.models.student import Student
from app.models.tag import Tag
from app.models.timeline_event import TimelineEvent
from app.models.user import User


client = TestClient(app)


@pytest.fixture(autouse=True)
def encryption_key(monkeypatch):
    monkeypatch.setenv("APP_ENCRYPTION_KEY", base64.urlsafe_b64encode(b"a" * 32).decode("ascii"))


def setup_function():
    with SessionLocal() as db:
        for model in (
            AISuggestionFeedback,
            AIWorkflowRun,
            Schedule,
            CustomerTag,
            Tag,
            AISuggestion,
            CustomerProfile,
            ChatMessage,
            TimelineEvent,
            AuditLog,
            Student,
            Customer,
            Organization,
            User,
        ):
            db.execute(delete(model))
        db.commit()


def test_sales_agent_routes_safely_and_keeps_human_gate():
    register = client.post(
        "/auth/register",
        json={"username": "agent_owner", "password": "Test123!"},
    )
    assert register.status_code == 201
    login = client.post(
        "/auth/token",
        data={"username": "agent_owner", "password": "Test123!"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    customer = client.post(
        "/customers",
        headers=headers,
        json={"name": "Agent 客户", "phone": "13800138000"},
    )
    assert customer.status_code == 201
    customer_id = customer.json()["id"]

    response = client.post(
        f"/customers/{customer_id}/agent/run",
        headers=headers,
        json={"task": "auto", "instruction": "请帮我生成标签建议"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["agent_name"] == "sales-copilot-v2"
    assert body["intent"] == "tag"
    assert body["selected_tool"] == "generate_tag_suggestions"
    assert body["planned_by"] == "mock"
    assert body["planner_run_id"] is not None
    assert body["human_confirmation_required"] is True
    assert body["workflow"]["next_action"] == "confirm_profile"
    assert any(item["name"] == "human_confirmation.require" for item in body["tool_trace"])
    with SessionLocal() as db:
        planning_run = db.query(AIWorkflowRun).filter_by(id=body["planner_run_id"]).one()
        assert planning_run.goal == "agent_plan"
        assert planning_run.result_json == {
            "status": "succeeded",
            "selected_tool": "generate_tag_suggestions",
            "human_confirmation_required": True,
        }


def test_sales_agent_respects_customer_scope():
    first = client.post("/auth/register", json={"username": "agent_first", "password": "Test123!"})
    second = client.post("/auth/register", json={"username": "agent_second", "password": "Test123!"})
    assert first.status_code == second.status_code == 201
    first_login = client.post("/auth/token", data={"username": "agent_first", "password": "Test123!"})
    second_login = client.post("/auth/token", data={"username": "agent_second", "password": "Test123!"})
    first_headers = {"Authorization": f"Bearer {first_login.json()['access_token']}"}
    second_headers = {"Authorization": f"Bearer {second_login.json()['access_token']}"}
    customer = client.post("/customers", headers=first_headers, json={"name": "私有 Agent 客户", "phone": "13800138001"})
    assert customer.status_code == 201

    denied = client.post(
        f"/customers/{customer.json()['id']}/agent/run",
        headers=second_headers,
        json={"task": "reply"},
    )
    assert denied.status_code == 404


def test_auto_agent_waits_after_latest_sales_message_instead_of_generating_reply():
    register = client.post("/auth/register", json={"username": "agent_wait", "password": "Test123!"})
    assert register.status_code == 201
    login = client.post("/auth/token", data={"username": "agent_wait", "password": "Test123!"})
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    customer = client.post("/customers", headers=headers, json={"name": "等待回复客户", "phone": "13800138002"})
    customer_id = customer.json()["id"]

    # 本用例只验证会话轮次，不需要再跑一遍回复工作流；直接准备一条已发送消息，
    # 模拟销售完成了人工审核与发送后的真实状态。
    with SessionLocal() as db:
        db.add(
            ChatMessage(
                customer_id=customer_id,
                user_id=1,
                wecom_message_id="agent-wait-outbound",
                direction="outbound",
                message_type="text",
                content_masked="您好，课程安排如下。",
                sent_at=datetime.now(timezone.utc),
            )
        )
        db.commit()

    response = client.post(f"/customers/{customer_id}/agent/run", headers=headers, json={"task": "auto"})
    assert response.status_code == 200
    body = response.json()
    assert body["intent"] == "wait"
    assert body["selected_tool"] == "wait_for_customer_reply"
    assert body["planned_by"] == "rule_based"
    assert body["workflow"]["suggestion_ids"] == []
