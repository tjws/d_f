from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.db.session import SessionLocal
from app.main import app
from app.models.ai_suggestion import AISuggestion
from app.models.ai_suggestion_feedback import AISuggestionFeedback
from app.models.audit_log import AuditLog
from app.models.chat_message import ChatMessage
from app.models.customer import Customer
from app.models.customer_profile import CustomerProfile
from app.models.customer_tag import CustomerTag
from app.models.tag import Tag
from app.models.timeline_event import TimelineEvent
from app.models.user import User


client = TestClient(app)


def setup_function():
    with SessionLocal() as db:
        for model in (ChatMessage, TimelineEvent, AuditLog, AISuggestionFeedback, CustomerTag, Tag, AISuggestion, CustomerProfile, Customer, User):
            db.execute(delete(model))
        db.commit()


def _headers_and_customer() -> tuple[dict[str, str], int]:
    register = client.post("/auth/register", json={"username": "pending_owner", "password": "Test123!"})
    assert register.status_code == 201
    login = client.post("/auth/token", data={"username": "pending_owner", "password": "Test123!"})
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    customer = client.post("/customers", headers=headers, json={"name": "待处理客户", "phone": "13800001000"})
    assert customer.status_code == 201
    return headers, customer.json()["id"]


def test_pending_actions_aggregates_four_types_and_filters_scope():
    headers, customer_id = _headers_and_customer()
    with SessionLocal() as db:
        owner = db.query(User).filter_by(username="pending_owner").one()
        now = datetime.now(timezone.utc)
        db.add(CustomerProfile(customer_id=customer_id, version=1, status="draft", dimensions_json={"next_action": "回访"}, evidence_json=[], model_name="test", model_version="1", prompt_version="test", created_at=now))
        db.add(AISuggestion(customer_id=customer_id, user_id=owner.id, suggestion_type="reply", content_json={"text": "您好，请问试听时间方便吗？"}, evidence_json=[], status="draft", model_name="test", model_version="1", prompt_version="test", created_at=now))
        db.add(AISuggestion(customer_id=customer_id, user_id=owner.id, suggestion_type="schedule", content_json={"title": "三天后电话跟进"}, evidence_json=[], status="edited", model_name="test", model_version="1", prompt_version="test", created_at=now))
        tag = Tag(key="high_intent", name="高意向", category="意向", description="需要人工确认", color="#2563EB", status="active")
        db.add(tag)
        db.flush()
        db.add(CustomerTag(customer_id=customer_id, tag_id=tag.id, source="ai", status="suggested", evidence_json=[], created_by=owner.id, created_at=now))
        db.commit()

    response = client.get("/pending-actions", headers=headers)
    assert response.status_code == 200
    assert {item["action_type"] for item in response.json()["items"]} == {"profile", "reply", "schedule", "tag"}
    assert client.get("/pending-actions?action_type=reply", headers=headers).json()["total"] == 1

    second = client.post("/auth/register", json={"username": "pending_other", "password": "Test123!"})
    assert second.status_code == 201
    other_login = client.post("/auth/token", data={"username": "pending_other", "password": "Test123!"})
    denied_items = client.get("/pending-actions", headers={"Authorization": f"Bearer {other_login.json()['access_token']}"})
    assert denied_items.status_code == 200
    assert denied_items.json()["items"] == []


def test_accepted_reply_stays_pending_until_mock_message_is_sent():
    headers, customer_id = _headers_and_customer()
    with SessionLocal() as db:
        owner = db.query(User).filter_by(username="pending_owner").one()
        suggestion = AISuggestion(
            customer_id=customer_id,
            user_id=owner.id,
            suggestion_type="reply",
            content_json={"text": "您好，这里是 AI 草稿"},
            evidence_json=[],
            status="draft",
            model_name="test",
            model_version="1",
            prompt_version="test",
        )
        db.add(suggestion)
        db.commit()
        suggestion_id = suggestion.id

    accepted = client.post(
        f"/customers/{customer_id}/suggestions/{suggestion_id}/accept",
        headers=headers,
    )
    assert accepted.status_code == 200

    pending_before_send = client.get(
        "/pending-actions?action_type=reply",
        headers=headers,
    )
    assert pending_before_send.status_code == 200
    assert pending_before_send.json()["total"] == 1
    assert pending_before_send.json()["items"][0]["status"] == "accepted"

    sent = client.post(
        f"/customers/{customer_id}/chat-messages/mock",
        headers=headers,
        json={
            "wecom_message_id": "pending-reply-outbound-001",
            "direction": "outbound",
            "message_type": "text",
            "content": "您好，这里是人工确认后的回复",
            "suggestion_id": suggestion_id,
        },
    )
    assert sent.status_code == 201
    assert sent.json()["suggestion_id"] == suggestion_id

    pending_after_send = client.get(
        "/pending-actions?action_type=reply",
        headers=headers,
    )
    assert pending_after_send.status_code == 200
    assert pending_after_send.json()["total"] == 0
