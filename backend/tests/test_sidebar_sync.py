from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.session import SessionLocal
from app.core.crypto import encrypt_text
from app.main import app
from app.models.chat_message import ChatMessage
from app.models.customer import Customer
from app.models.timeline_event import TimelineEvent
from app.models.user import User


client = TestClient(app)


def setup_function():
    with SessionLocal() as db:
        for model in (ChatMessage, TimelineEvent, Customer, User):
            db.query(model).delete()
        db.commit()


def test_sidebar_sync_returns_only_rows_after_cursors():
    assert client.post("/auth/register", json={"username": "sync_owner", "password": "Test123!"}).status_code == 201
    login = client.post("/auth/token", data={"username": "sync_owner", "password": "Test123!"})
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    customer = client.post("/customers", headers=headers, json={"name": "增量客户", "phone": "13800002000"})
    customer_id = customer.json()["id"]

    first = client.post(
        f"/customers/{customer_id}/chat-messages/mock",
        headers=headers,
        json={"wecom_message_id": "sync-1", "direction": "inbound", "message_type": "text", "content": "第一条"},
    )
    assert first.status_code == 201
    first_id = first.json()["id"]
    with SessionLocal() as db:
        owner = db.scalar(select(User).where(User.username == "sync_owner"))
        db.add(TimelineEvent(customer_id=customer_id, operator_id=owner.id, occurred_at=datetime.now(timezone.utc), event_type="manual", summary_encrypted=encrypt_text("一次人工跟进"), source="manual"))
        db.commit()

    response = client.get(f"/customers/{customer_id}/sidebar-sync?after_message_id={first_id}&after_timeline_id=0", headers=headers)
    assert response.status_code == 200
    assert response.json()["messages"] == []
    assert len(response.json()["timeline_events"]) >= 1
    assert response.json()["next_message_id"] == first_id
