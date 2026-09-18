from datetime import datetime
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.ai_suggestion import AISuggestion
from app.models.ai_suggestion_feedback import AISuggestionFeedback
from app.models.ai_workflow_run import AIWorkflowRun
from app.models.ai_rag_interaction import AIRagInteraction
from app.models.customer_profile import CustomerProfile
from app.models.customer_tag import CustomerTag


class AIDashboardDAO:
    """看板所需的时间窗口查询；指标计算放在 Service。"""
    def suggestions(self, db: Session, start: datetime, end: datetime) -> list[AISuggestion]:
        return list(db.scalars(select(AISuggestion).where(AISuggestion.created_at >= start, AISuggestion.created_at < end)).all())
    def profiles(self, db: Session, start: datetime, end: datetime) -> list[CustomerProfile]:
        return list(db.scalars(select(CustomerProfile).where(CustomerProfile.created_at >= start, CustomerProfile.created_at < end)).all())
    def ai_tags(self, db: Session, start: datetime, end: datetime) -> list[CustomerTag]:
        return list(db.scalars(select(CustomerTag).where(CustomerTag.source == "ai", CustomerTag.created_at >= start, CustomerTag.created_at < end)).all())
    def feedback(self, db: Session, start: datetime, end: datetime) -> list[AISuggestionFeedback]:
        return list(db.scalars(select(AISuggestionFeedback).where(AISuggestionFeedback.created_at >= start, AISuggestionFeedback.created_at < end)).all())
    def workflow_runs(self, db: Session, start: datetime, end: datetime) -> list[AIWorkflowRun]:
        return list(db.scalars(select(AIWorkflowRun).where(AIWorkflowRun.created_at >= start, AIWorkflowRun.created_at < end)).all())
    def rag_interactions(self, db: Session, start: datetime, end: datetime) -> list[AIRagInteraction]:
        return list(db.scalars(select(AIRagInteraction).where(AIRagInteraction.created_at >= start, AIRagInteraction.created_at < end)).all())
