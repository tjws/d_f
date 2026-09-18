import uuid
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.session import SessionLocal
from app.main import app
from app.models.ai_workflow_run import AIWorkflowRun
from app.models.customer import Customer
from app.models.user import User


client = TestClient(app)


def _user_headers(role: str) -> tuple[dict[str, str], int]:
    username = f"workflow_admin_{uuid.uuid4().hex[:8]}"
    password = "Test123!"
    assert client.post("/auth/register", json={"username": username, "password": password}).status_code == 201
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.username == username))
        assert user is not None
        user.role = role
        db.commit()
        user_id = user.id
    login = client.post("/auth/token", data={"username": username, "password": password})
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}, user_id


def test_admin_workflow_history_exposes_safe_summary_and_blocks_sales():
    admin_headers, admin_id = _user_headers("admin")
    with SessionLocal() as db:
        customer = Customer(name="运行历史测试客户", phone=f"139{uuid.uuid4().int % 10**8:08d}", owner_id=admin_id)
        db.add(customer)
        db.flush()
        run = AIWorkflowRun(
            customer_id=customer.id,
            actor_user_id=admin_id,
            goal="reply",
            provider_name="bailian",
            status="succeeded",
            attempt_count=1,
            result_json={"status": "waiting_human", "suggestion_ids": [11], "next_action": "review_reply", "secret": "must-not-leak"},
        )
        db.add(run)
        db.commit()
        run_id = run.id

    response = client.get("/admin/ai-workflow-runs?provider_name=bailian&status=waiting_human", headers=admin_headers)
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] >= 1
    item = next(item for item in payload["items"] if item["id"] == run_id)
    assert item["status"] == "waiting_human"
    assert item["suggestion_count"] == 1
    assert "secret" not in response.text
    assert "result_json" not in response.text

    sales_headers, _ = _user_headers("sales")
    denied = client.get("/admin/ai-workflow-runs", headers=sales_headers)
    assert denied.status_code == 403


def test_admin_can_recover_stale_running_workflow_after_explicit_confirmation():
    admin_headers, admin_id = _user_headers("admin")
    stale_at = datetime.now(timezone.utc) - timedelta(minutes=10)
    with SessionLocal() as db:
        customer = Customer(
            name="Worker 失联恢复测试客户",
            phone=f"138{uuid.uuid4().int % 10**8:08d}",
            owner_id=admin_id,
        )
        db.add(customer)
        db.flush()
        run = AIWorkflowRun(
            customer_id=customer.id,
            actor_user_id=admin_id,
            goal="reply",
            provider_name="mock",
            status="running",
            attempt_count=1,
            started_at=stale_at,
            heartbeat_at=stale_at,
            result_json={"status": "running", "suggestion_ids": []},
        )
        db.add(run)
        db.commit()
        run_id = run.id

    not_confirmed = client.post(
        "/admin/ai-workflow-runs/recover-stale",
        json={"confirm": False},
        headers=admin_headers,
    )
    assert not_confirmed.status_code == 400

    response = client.post(
        "/admin/ai-workflow-runs/recover-stale",
        json={"confirm": True, "stale_after_seconds": 60, "limit": 50},
        headers=admin_headers,
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["marked_failed"] >= 1
    assert run_id in payload["run_ids"]

    with SessionLocal() as db:
        recovered = db.get(AIWorkflowRun, run_id)
        assert recovered is not None
        assert recovered.status == "failed"
        assert recovered.error_code == "worker_lost"
        assert recovered.heartbeat_at is None
        assert recovered.result_json["status"] == "failed"
        assert recovered.result_json["recovery"] == "stale_worker"
