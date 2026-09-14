from sqlalchemy import delete, select

from app.ai.persistence_node import persist_suggestion_node
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.ai_suggestion import AISuggestion
from app.models.audit_log import AuditLog
from app.models.customer import Customer
from app.models.customer_profile import CustomerProfile
from app.models.user import User


def test_persistence_node_saves_draft_and_audit_log():
    with SessionLocal() as db:
        user = User(
            username="langgraph_persistence_admin",
            full_name="LangGraph Persistence Test",
            hashed_password=hash_password("unused-password"),
            role="admin",
        )
        db.add(user)
        db.flush()

        customer = Customer(
            owner_id=user.id,
            name="LangGraph 持久化测试客户",
            phone="13900239000",
            interested_subject="英语",
        )
        db.add(customer)
        db.flush()
        db.add(
            CustomerProfile(
                customer_id=customer.id,
                version=1,
                status="confirmed",
                dimensions_json={"next_action": "确认学习目标"},
                evidence_json=[],
            )
        )
        db.commit()
        customer_id = customer.id
        user_id = user.id

    result = persist_suggestion_node(
        {
            "customer_id": customer_id,
            "actor_user_id": user_id,
            "suggestions": [
                {
                    "suggestion_type": "reply",
                    "content": {"text": "这是一条测试草稿"},
                    "evidence_level": "normal",
                    "model_name": "mock-rules",
                    "model_version": "1",
                }
            ],
        }
    )

    assert result["status"] == "waiting_human"
    assert len(result["suggestion_ids"]) == 1

    with SessionLocal() as db:
        suggestion = db.scalar(
            select(AISuggestion).where(AISuggestion.id == result["suggestion_ids"][0])
        )
        audit_log = db.scalar(
            select(AuditLog).where(
                AuditLog.target_type == "ai_suggestion",
                AuditLog.target_id == str(suggestion.id),
            )
        )

        assert suggestion.status == "draft"
        assert suggestion.content_json == {"text": "这是一条测试草稿"}
        assert audit_log is not None
        assert audit_log.action == "customer.ai_reply_generated"

        db.execute(delete(Customer).where(Customer.id == customer_id))
        db.execute(delete(User).where(User.id == user_id))
        db.commit()
