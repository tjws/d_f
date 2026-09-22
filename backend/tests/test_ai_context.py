import base64
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import delete

from app.ai.context_builder import build_customer_context
from app.core.crypto import encrypt_text
from app.db.session import SessionLocal
from app.models.chat_message import ChatMessage
from app.models.customer import Customer
from app.models.customer_profile import CustomerProfile
from app.models.schedule import Schedule
from app.models.timeline_event import TimelineEvent


@pytest.fixture(autouse=True)
def encryption_key(monkeypatch):
    """为测试中的加密聊天内容和时间线提供固定密钥。"""

    monkeypatch.setenv(
        "APP_ENCRYPTION_KEY",
        base64.urlsafe_b64encode(b"a" * 32).decode("ascii"),
    )


@pytest.fixture
def context_customer_id():
    with SessionLocal() as db:
        customer = Customer(
            name="AI 上下文测试客户",
            phone="13900139000",
            student_name="上下文测试学生",
            grade="初一",
            interested_subject="数学",
            stage="new",
        )
        db.add(customer)
        db.flush()

        db.add_all(
            [
                CustomerProfile(
                    customer_id=customer.id,
                    version=1,
                    status="draft",
                    dimensions_json={"next_action": "draft"},
                    evidence_json=[],
                ),
                CustomerProfile(
                    customer_id=customer.id,
                    version=2,
                    status="confirmed",
                    dimensions_json={"next_action": "confirmed"},
                    evidence_json=[{"source": "test"}],
                ),
            ]
        )
        db.add(
            ChatMessage(
                customer_id=customer.id,
                wecom_message_id="ai-context-test-message",
                direction="inbound",
                message_type="text",
                content_encrypted=encrypt_text("原始手机号 13900139000"),
                content_masked="原始手机号 139****9000",
                sent_at=datetime.now(timezone.utc),
            )
        )
        db.add(
            TimelineEvent(
                customer_id=customer.id,
                occurred_at=datetime.now(timezone.utc),
                event_type="wecom_message",
                summary_encrypted=encrypt_text("家长咨询数学课程"),
                source="wecom",
            )
        )
        db.add(
            Schedule(
                customer_id=customer.id,
                title="试听确认回访",
                due_at=datetime.now(timezone.utc),
                status="completed",
                outcome="appointment",
                completion_note="家长电话 13800138000，已约好周末试听",
                completed_at=datetime.now(timezone.utc),
                evidence_json=[],
            )
        )
        db.commit()
        customer_id = customer.id

    yield customer_id

    with SessionLocal() as db:
        db.execute(delete(Customer).where(Customer.id == customer_id))
        db.commit()


def test_context_builder_masks_sensitive_data_and_uses_confirmed_profile(
    context_customer_id,
):
    with SessionLocal() as db:
        context = build_customer_context(db, context_customer_id)

    assert context["customer"]["phone"] == "139****9000"
    assert context["confirmed_profile"]["dimensions"] == {
        "next_action": "confirmed"
    }
    assert context["messages"][0]["content"] == "原始手机号 139****9000"
    assert context["timeline_events"][0]["summary"] == "家长咨询数学课程"
    assert context["completed_follow_ups"] == [
        {
            "id": context["completed_follow_ups"][0]["id"],
            "title": "试听确认回访",
            "outcome": "appointment",
            "completion_note": "家长电话 138****8000，已约好周末试听",
            "completed_at": context["completed_follow_ups"][0]["completed_at"],
        }
    ]


def test_context_builder_rejects_unknown_customer():
    with SessionLocal() as db:
        with pytest.raises(ValueError, match="customer 999999 not found"):
            build_customer_context(db, 999999)


def test_context_builder_does_not_reuse_old_parent_question_after_sales_reply(context_customer_id):
    """最新消息为销售发送时，RAG 不应回头检索更早的家长问题。"""

    with SessionLocal() as db:
        db.add(
            ChatMessage(
                customer_id=context_customer_id,
                wecom_message_id="ai-context-outbound-latest",
                direction="outbound",
                message_type="text",
                content_masked="销售已回复课程问题",
                sent_at=datetime.now(timezone.utc) + timedelta(minutes=1),
            )
        )
        db.commit()
        context = build_customer_context(db, context_customer_id)

    assert context["knowledge_policy"]["query"] == ""
