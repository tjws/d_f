from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.db.session import SessionLocal
from app.main import app
from app.models.ai_suggestion import AISuggestion
from app.models.ai_suggestion_feedback import AISuggestionFeedback
from app.models.customer import Customer
from app.models.schedule import Schedule
from app.models.user import User


client = TestClient(app)


def setup_function():
    with SessionLocal() as db:
        for model in (AISuggestionFeedback, Schedule, AISuggestion, Customer, User):
            db.execute(delete(model))
        db.commit()


def test_my_work_returns_personal_schedule_buckets_and_ai_reviews():
    register = client.post("/auth/register", json={"username": "work_owner", "password": "Test123!"})
    assert register.status_code == 201
    login = client.post("/auth/token", data={"username": "work_owner", "password": "Test123!"})
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    customer = client.post("/customers", headers=headers, json={"name": "跟进客户", "phone": "13800002000"})
    assert customer.status_code == 201
    customer_id = customer.json()["id"]

    with SessionLocal() as db:
        owner = db.query(User).filter_by(username="work_owner").one()
        now = datetime.now(timezone.utc)
        db.add(AISuggestion(customer_id=customer_id, user_id=owner.id, suggestion_type="reply", content_json={"text": "待审核回复"}, evidence_json=[], status="draft", model_name="test", model_version="1", prompt_version="test"))
        db.add_all(
            [
                Schedule(customer_id=customer_id, user_id=owner.id, title="已逾期电话", due_at=now - timedelta(hours=2), priority="high", status="confirmed", evidence_json=[]),
                Schedule(customer_id=customer_id, user_id=owner.id, title="今天跟进", due_at=now + timedelta(hours=1), priority="normal", status="confirmed", evidence_json=[]),
                Schedule(customer_id=customer_id, user_id=owner.id, title="本周回访", due_at=now + timedelta(days=2), priority="low", status="confirmed", evidence_json=[]),
            ]
        )
        db.commit()

    response = client.get("/my-work", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["summary"]["review"] == 1
    assert body["summary"]["overdue"] == 1
    assert body["summary"]["today"] == 1
    assert body["summary"]["upcoming"] == 1
    assert len(client.get("/my-work?bucket=overdue", headers=headers).json()["items"]) == 1


def test_my_work_does_not_show_another_users_schedule():
    first = client.post("/auth/register", json={"username": "work_first", "password": "Test123!"})
    second = client.post("/auth/register", json={"username": "work_second", "password": "Test123!"})
    assert first.status_code == second.status_code == 201
    first_login = client.post("/auth/token", data={"username": "work_first", "password": "Test123!"})
    second_login = client.post("/auth/token", data={"username": "work_second", "password": "Test123!"})
    first_headers = {"Authorization": f"Bearer {first_login.json()['access_token']}"}
    second_headers = {"Authorization": f"Bearer {second_login.json()['access_token']}"}
    customer = client.post("/customers", headers=first_headers, json={"name": "私有日程客户", "phone": "13800002001"})
    with SessionLocal() as db:
        first_user = db.query(User).filter_by(username="work_first").one()
        db.add(Schedule(customer_id=customer.json()["id"], user_id=first_user.id, title="不可见日程", due_at=datetime.now(timezone.utc), priority="normal", status="confirmed", evidence_json=[]))
        db.commit()
    response = client.get("/my-work", headers=second_headers)
    assert response.status_code == 200
    assert response.json()["summary"]["today"] == 0


def test_old_reply_draft_is_historical_and_can_be_closed_without_deleting():
    register = client.post("/auth/register", json={"username": "history_owner", "password": "Test123!"})
    login = client.post("/auth/token", data={"username": "history_owner", "password": "Test123!"})
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    customer = client.post("/customers", headers=headers, json={"name": "历史草稿客户", "phone": "13800002002"})
    with SessionLocal() as db:
        owner = db.query(User).filter_by(username="history_owner").one()
        suggestion = AISuggestion(
            customer_id=customer.json()["id"], user_id=owner.id, suggestion_type="reply",
            content_json={"text": "旧回复草稿"}, evidence_json=[], status="draft",
            model_name="test", model_version="1", prompt_version="test",
            created_at=datetime.now(timezone.utc) - timedelta(days=8),
        )
        db.add(suggestion)
        db.commit()
        suggestion_id = suggestion.id

    response = client.get("/my-work", headers=headers)
    assert response.status_code == 200
    assert response.json()["summary"]["review"] == 0
    assert response.json()["summary"]["historical"] == 1
    historical = client.get("/my-work?bucket=historical", headers=headers)
    assert historical.json()["items"][0]["action_type"] == "reply"

    closed = client.post(f"/pending-actions/reply/{suggestion_id}/dismiss-historical", headers=headers)
    assert closed.status_code == 200
    assert closed.json()["closed"] is True
    with SessionLocal() as db:
        assert db.get(AISuggestion, suggestion_id).status == "expired"


def test_current_reply_draft_can_be_closed_from_workbench():
    register = client.post("/auth/register", json={"username": "close_owner", "password": "Test123!"})
    login = client.post("/auth/token", data={"username": "close_owner", "password": "Test123!"})
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    customer = client.post("/customers", headers=headers, json={"name": "关闭建议客户", "phone": "13800002003"})
    with SessionLocal() as db:
        owner = db.query(User).filter_by(username="close_owner").one()
        suggestion = AISuggestion(
            customer_id=customer.json()["id"], user_id=owner.id, suggestion_type="reply",
            content_json={"text": "近期回复草稿"}, evidence_json=[], status="draft",
            model_name="test", model_version="1", prompt_version="test",
        )
        db.add(suggestion)
        db.commit()
        suggestion_id = suggestion.id

    closed = client.post(f"/pending-actions/reply/{suggestion_id}/dismiss", headers=headers)
    assert closed.status_code == 200
    with SessionLocal() as db:
        assert db.get(AISuggestion, suggestion_id).status == "expired"
