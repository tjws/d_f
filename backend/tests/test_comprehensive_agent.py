from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.agent.comprehensive_planner import ALLOWED_AGENT_TOOLS, MockComprehensivePlanner
from app.agent.synthesis import synthesize_comprehensive_suggestion
from app.db.session import SessionLocal
from app.main import app
from app.models.ai_suggestion import AISuggestion
from app.models.ai_workflow_run import AIWorkflowRun
from app.models.audit_log import AuditLog
from app.models.customer import Customer
from app.models.user import User


client = TestClient(app)


def test_mock_comprehensive_planner_uses_only_five_read_only_tools():
    plan = MockComprehensivePlanner().plan({}, None)

    assert plan["provider_name"] == "mock"
    assert plan["tool_names"] == list(ALLOWED_AGENT_TOOLS)
    assert len(plan["tool_names"]) == 5


def test_comprehensive_synthesis_marks_missing_inputs_and_keeps_human_gate():
    payload = synthesize_comprehensive_suggestion(
        {"interested_subject": "数学"},
        [
            {
                "tool_name": "knowledge.search",
                "status": "incomplete",
                "summary": "没有达到阈值",
                "data": {"titles": []},
                "evidence": [],
                "missing_inputs": ["verified_knowledge_match"],
            },
            {
                "tool_name": "course_openings.read",
                "status": "ok",
                "summary": "静态课程资料",
                "data": {},
                "evidence": [],
                "missing_inputs": ["realtime_seat_availability"],
            },
        ],
    )

    assert payload["evidence_level"] == "insufficient"
    assert payload["content"]["uncertainty"] == "high"
    assert payload["content"]["missing_inputs"] == [
        "verified_knowledge_match",
        "realtime_seat_availability",
    ]
    assert "人工" in payload["content"]["text"]


def test_comprehensive_agent_endpoint_persists_five_step_trace(monkeypatch):
    monkeypatch.setenv("AI_AGENT_PLANNER_PROVIDER", "mock")
    username = f"comprehensive_{uuid4().hex[:10]}"
    password = "Test123!"
    register = client.post("/auth/register", json={"username": username, "password": password})
    assert register.status_code == 201
    login = client.post("/auth/token", data={"username": username, "password": password})
    assert login.status_code == 200
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    created = client.post("/customers", headers=headers, json={"name": "综合分析测试客户", "phone": "13800138099"})
    assert created.status_code == 201
    customer_id = created.json()["id"]

    try:
        response = client.post(
            f"/customers/{customer_id}/agent/run",
            headers=headers,
            json={"task": "comprehensive", "instruction": "整理全部可用资料"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["intent"] == "comprehensive"
        assert len(body["steps"]) == 5
        assert body["workflow"]["status"] == "waiting_human"
        assert body["workflow"]["suggestion_ids"]
        assert body["human_confirmation_required"] is True
        assert any(item["name"] == "human_confirmation.require" for item in body["tool_trace"])
    finally:
        with SessionLocal() as db:
            db.execute(delete(AISuggestion).where(AISuggestion.customer_id == customer_id))
            db.execute(delete(AIWorkflowRun).where(AIWorkflowRun.customer_id == customer_id))
            db.execute(delete(AuditLog).where(AuditLog.actor_user_id == register.json()["id"]))
            db.execute(delete(Customer).where(Customer.id == customer_id))
            db.execute(delete(User).where(User.id == register.json()["id"]))
            db.commit()


def test_checkpointed_comprehensive_agent_supports_correction_and_resume(monkeypatch):
    """分步模式不会提前生成草稿，人工修正后可逐次继续到人工确认点。"""

    monkeypatch.setenv("AI_AGENT_PLANNER_PROVIDER", "mock")
    username = f"checkpoint_{uuid4().hex[:10]}"
    password = "Test123!"
    register = client.post("/auth/register", json={"username": username, "password": password})
    assert register.status_code == 201
    login = client.post("/auth/token", data={"username": username, "password": password})
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    created = client.post(
        "/customers",
        headers=headers,
        json={"name": "分步 Agent 测试客户", "phone": "13800138100"},
    )
    assert created.status_code == 201
    customer_id = created.json()["id"]
    run_id = None

    try:
        start = client.post(
            f"/customers/{customer_id}/agent/run",
            headers=headers,
            json={"task": "comprehensive", "execution_mode": "checkpointed"},
        )
        assert start.status_code == 200
        start_body = start.json()
        run_id = start_body["workflow"]["run_id"]
        assert start_body["workflow"]["status"] == "paused"
        assert start_body["workflow"]["next_action"] == "resume_agent"
        assert start_body["steps"] == []

        corrected = client.post(
            f"/customers/{customer_id}/agent/runs/{run_id}/control",
            headers=headers,
            json={
                "action": "correct",
                "correction": {"skip_tools": ["orders.list"], "note": "本次不查看订单"},
            },
        )
        assert corrected.status_code == 200
        assert corrected.json()["workflow"]["status"] == "paused"

        final_body = corrected.json()
        for _ in range(5):
            if final_body["workflow"]["status"] == "waiting_human":
                break
            resumed = client.post(
                f"/customers/{customer_id}/agent/runs/{run_id}/control",
                headers=headers,
                json={"action": "resume", "step_limit": 1},
            )
            assert resumed.status_code == 200
            final_body = resumed.json()

        assert final_body["workflow"]["status"] == "waiting_human"
        assert len(final_body["steps"]) == 5
        assert any(step["tool_name"] == "orders.list" and step["status"] == "skipped" for step in final_body["steps"])
        assert final_body["workflow"]["suggestion_ids"]
    finally:
        with SessionLocal() as db:
            db.execute(delete(AISuggestion).where(AISuggestion.customer_id == customer_id))
            db.execute(delete(AIWorkflowRun).where(AIWorkflowRun.customer_id == customer_id))
            db.execute(delete(AuditLog).where(AuditLog.actor_user_id == register.json()["id"]))
            db.execute(delete(Customer).where(Customer.id == customer_id))
            db.execute(delete(User).where(User.id == register.json()["id"]))
            db.commit()


def test_queue_mode_delegates_comprehensive_agent_to_worker(monkeypatch):
    """Compose 队列模式下 API 快速返回，Worker 执行后仍生成同一条人工草稿。"""

    monkeypatch.setenv("AI_AGENT_PLANNER_PROVIDER", "mock")
    monkeypatch.setenv("AI_WORKFLOW_EXECUTION_MODE", "queue")
    from app.workers import ai_workflow_tasks
    from app.services.comprehensive_agent_service import execute_comprehensive_agent_run

    sent: list[int] = []
    monkeypatch.setattr(ai_workflow_tasks.execute_comprehensive_agent_task, "send", lambda run_id: sent.append(run_id))
    username = f"queue_{uuid4().hex[:10]}"
    password = "Test123!"
    register = client.post("/auth/register", json={"username": username, "password": password})
    assert register.status_code == 201
    login = client.post("/auth/token", data={"username": username, "password": password})
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    created = client.post(
        "/customers",
        headers=headers,
        json={"name": "队列 Agent 测试客户", "phone": "13800138103"},
    )
    assert created.status_code == 201
    customer_id = created.json()["id"]

    try:
        response = client.post(
            f"/customers/{customer_id}/agent/run",
            headers=headers,
            json={"task": "comprehensive"},
        )
        assert response.status_code == 200
        body = response.json()
        run_id = body["workflow"]["run_id"]
        assert body["workflow"]["status"] == "queued"
        assert sent == [run_id]

        paused = client.post(
            f"/customers/{customer_id}/agent/runs/{run_id}/control",
            headers=headers,
            json={"action": "pause"},
        )
        assert paused.status_code == 200
        assert paused.json()["workflow"]["status"] == "paused"

        resumed = client.post(
            f"/customers/{customer_id}/agent/runs/{run_id}/control",
            headers=headers,
            json={"action": "resume", "step_limit": 5},
        )
        assert resumed.status_code == 200
        assert resumed.json()["workflow"]["status"] == "queued"
        assert sent == [run_id, run_id]

        execute_comprehensive_agent_run(run_id)
        status_response = client.get(
            f"/customers/{customer_id}/agent/runs/{run_id}",
            headers=headers,
        )
        assert status_response.status_code == 200
        finished = status_response.json()
        assert finished["workflow"]["status"] == "waiting_human"
        assert len(finished["steps"]) == 5
        assert finished["workflow"]["suggestion_ids"]
    finally:
        with SessionLocal() as db:
            db.execute(delete(AISuggestion).where(AISuggestion.customer_id == customer_id))
            db.execute(delete(AIWorkflowRun).where(AIWorkflowRun.customer_id == customer_id))
            db.execute(delete(AuditLog).where(AuditLog.actor_user_id == register.json()["id"]))
            db.execute(delete(Customer).where(Customer.id == customer_id))
            db.execute(delete(User).where(User.id == register.json()["id"]))
            db.commit()


def test_failed_comprehensive_agent_retry_keeps_successful_steps(monkeypatch):
    """综合 Agent 重试只移除失败步骤，避免重复执行已经完成的只读查询。"""

    monkeypatch.setenv("AI_WORKFLOW_EXECUTION_MODE", "queue")
    from app.workers import ai_workflow_tasks

    sent: list[int] = []
    monkeypatch.setattr(ai_workflow_tasks.execute_comprehensive_agent_task, "send", lambda run_id: sent.append(run_id))
    register = client.post("/auth/register", json={"username": f"retry_agent_{uuid4().hex[:8]}", "password": "Test123!"})
    assert register.status_code == 201
    login = client.post("/auth/token", data={"username": register.json()["username"], "password": "Test123!"})
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    customer = client.post("/customers", headers=headers, json={"name": "综合 Agent 重试客户", "phone": "13800138003"})
    customer_id = customer.json()["id"]
    plan_tools = list(ALLOWED_AGENT_TOOLS)
    with SessionLocal() as db:
        run = AIWorkflowRun(
            customer_id=customer_id,
            actor_user_id=register.json()["id"],
            goal="agent_comprehensive",
            provider_name="mock",
            status="failed",
            attempt_count=1,
            result_json={
                "status": "failed",
                "plan_tool_names": plan_tools,
                "plan_rationale": "test plan",
                "agent_steps": [
                    {"step": 1, "tool_name": plan_tools[0], "status": "ok", "summary": "done", "data": {}, "evidence": [], "missing_inputs": []},
                    {"step": 2, "tool_name": plan_tools[1], "status": "error", "summary": "failed", "data": {}, "evidence": [], "missing_inputs": [plan_tools[1]]},
                ],
            },
        )
        db.add(run)
        db.commit()
        db.refresh(run)
        run_id = run.id

    response = client.post(
        f"/customers/{customer_id}/agent/runs/{run_id}/retry",
        headers=headers,
        json={"confirm": True},
    )
    assert response.status_code == 200
    assert response.json()["workflow"]["status"] == "queued"
    assert [step["tool_name"] for step in response.json()["steps"]] == [plan_tools[0]]
    assert sent == [run_id]
    with SessionLocal() as db:
        db.execute(delete(AIWorkflowRun).where(AIWorkflowRun.id == run_id))
        db.execute(delete(Customer).where(Customer.id == customer_id))
        db.execute(delete(User).where(User.id == register.json()["id"]))
        db.commit()
