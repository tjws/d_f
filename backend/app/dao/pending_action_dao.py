"""待处理 AI 动作的跨表只读查询。"""

from sqlalchemy import and_, exists, or_, select
from sqlalchemy.orm import Session

from app.models.ai_suggestion import AISuggestion
from app.models.customer import Customer
from app.models.customer_profile import CustomerProfile
from app.models.customer_tag import CustomerTag
from app.models.chat_message import ChatMessage
from app.models.tag import Tag


class PendingActionDAO:
    """聚合不同建议表；权限条件由 Service 从 customers 统一传入。"""

    def list_profiles(self, db: Session, customer_filters: list):
        statement = (
            select(CustomerProfile, Customer.name, Customer.stage)
            .join(Customer, Customer.id == CustomerProfile.customer_id)
            .where(CustomerProfile.status == "draft", *customer_filters)
            .order_by(CustomerProfile.created_at.desc(), CustomerProfile.id.desc())
        )
        return list(db.execute(statement).all())

    def list_suggestions(self, db: Session, customer_filters: list):
        statement = (
            select(AISuggestion, Customer.name, Customer.stage)
            .join(Customer, Customer.id == AISuggestion.customer_id)
            .where(
                or_(
                    AISuggestion.status.in_(("draft", "edited")),
                    and_(
                        AISuggestion.suggestion_type == "reply",
                        AISuggestion.status == "accepted",
                        ~exists(
                            select(ChatMessage.id).where(
                                ChatMessage.suggestion_id == AISuggestion.id,
                            )
                        ),
                    ),
                ),
                AISuggestion.suggestion_type.in_(("reply", "schedule")),
                *customer_filters,
            )
            .order_by(AISuggestion.created_at.desc(), AISuggestion.id.desc())
        )
        return list(db.execute(statement).all())

    def list_tags(self, db: Session, customer_filters: list):
        statement = (
            select(CustomerTag, Tag, Customer.name, Customer.stage)
            .join(Customer, Customer.id == CustomerTag.customer_id)
            .join(Tag, Tag.id == CustomerTag.tag_id)
            .where(CustomerTag.status == "suggested", *customer_filters)
            .order_by(CustomerTag.created_at.desc(), CustomerTag.id.desc())
        )
        return list(db.execute(statement).all())
