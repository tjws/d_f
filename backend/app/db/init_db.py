from app.db.base import Base
from app.db.session import engine

# 导入模型，让 SQLAlchemy 知道需要创建 Customer 表。
from app.models.customer import Customer
from app.models.ai_suggestion_feedback import AISuggestionFeedback
from app.models.course_order import CourseOrder
from app.models.service_ticket import ServiceTicket
from app.models.system_setting import SystemSetting
from app.models.sales_script import SalesScript
from app.models.knowledge_document import KnowledgeDocument
from app.models.knowledge_chunk import KnowledgeChunk
from app.models.ai_rag_interaction import AIRagInteraction
from app.models.rag_evaluation_case import RAGEvaluationCase
from app.models.ai_rollout_membership import AIRolloutMembership
from app.models.ai_rollout_daily_report import AIRolloutDailyReport


def init_db():
    """根据所有模型创建数据库表。"""

    Base.metadata.create_all(bind=engine)
