from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context
from pathlib import Path
import sys
import os
# 将 backend 加入 Python 搜索路径，
# 这样 Alembic 才能导入 backend/app 下的代码。
BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.db.base import Base
from app.models.audit_log import AuditLog
from app.models.chat_message import ChatMessage
from app.models.customer import Customer
from app.models.customer_profile import CustomerProfile
from app.models.ai_suggestion import AISuggestion
from app.models.tag import Tag
from app.models.customer_tag import CustomerTag
from app.models.schedule import Schedule
from app.models.integration_event import IntegrationEvent
from app.models.organization import Organization
from app.models.role_permission import RolePermission
from app.models.student import Student
from app.models.timeline_event import TimelineEvent
from app.models.user import User
from app.models.ai_workflow_run import AIWorkflowRun
from app.models.ai_suggestion_feedback import AISuggestionFeedback
from app.models.customer_transfer import CustomerTransfer
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
from app.models.churn_scoring_batch import ChurnScoringBatch
from app.models.churn_risk_prediction import ChurnRiskPrediction
from app.models.external_student_mapping import ExternalStudentMapping
from app.models.churn_risk_intervention import ChurnRiskIntervention
from app.models.churn_model_version import ChurnModelVersion

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Docker/生产环境通过环境变量提供数据库地址；本地仍可使用 alembic.ini 的 SQLite 默认值。
database_url = os.getenv("DATABASE_URL")
if database_url:
    config.set_main_option("sqlalchemy.url", database_url)

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
# Base.metadata 包含所有 SQLAlchemy 模型的表结构。
# 导入 Customer 是为了让它注册到 metadata 中。
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=url.startswith("sqlite"),
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            render_as_batch=connection.dialect.name == "sqlite",
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
