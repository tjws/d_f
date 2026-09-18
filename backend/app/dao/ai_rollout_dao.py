from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.ai_rollout_daily_report import AIRolloutDailyReport
from app.models.ai_rollout_membership import AIRolloutMembership


class AIRolloutDAO:
    """灰度名单和日报快照的数据访问，不在 DAO 中提交事务。"""

    def get_membership(self, db: Session, user_id: int) -> AIRolloutMembership | None:
        return db.scalar(select(AIRolloutMembership).where(AIRolloutMembership.user_id == user_id))

    def list_memberships(self, db: Session) -> list[AIRolloutMembership]:
        return list(db.scalars(select(AIRolloutMembership).order_by(AIRolloutMembership.created_at.desc())).all())

    def active_memberships(self, db: Session) -> list[AIRolloutMembership]:
        return list(db.scalars(select(AIRolloutMembership).where(AIRolloutMembership.status == "active")).all())

    def add_membership(self, db: Session, membership: AIRolloutMembership) -> None:
        db.add(membership)

    def get_report(self, db: Session, report_date: date, cohort: str) -> AIRolloutDailyReport | None:
        return db.scalar(
            select(AIRolloutDailyReport).where(
                AIRolloutDailyReport.report_date == report_date,
                AIRolloutDailyReport.cohort == cohort,
            )
        )

    def list_reports(self, db: Session, limit: int = 30) -> list[AIRolloutDailyReport]:
        return list(
            db.scalars(
                select(AIRolloutDailyReport)
                .order_by(AIRolloutDailyReport.report_date.desc())
                .limit(limit)
            ).all()
        )

    def add_report(self, db: Session, report: AIRolloutDailyReport) -> None:
        db.add(report)

