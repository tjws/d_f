"""客户流失评分的数据访问层。"""

from datetime import datetime

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models.churn_risk_prediction import ChurnRiskPrediction
from app.models.churn_risk_intervention import ChurnRiskIntervention
from app.models.churn_scoring_batch import ChurnScoringBatch
from app.models.customer import Customer
from app.models.external_student_mapping import ExternalStudentMapping
from app.models.student import Student


class ChurnRiskDAO:
    """只负责数据库读写，评分规则和事务由 Service 决定。"""

    def add_batch(self, db: Session, batch: ChurnScoringBatch) -> None:
        db.add(batch)

    def get_batch(self, db: Session, batch_id: int) -> ChurnScoringBatch | None:
        return db.get(ChurnScoringBatch, batch_id)

    def get_prediction(self, db: Session, prediction_id: int) -> ChurnRiskPrediction | None:
        return db.get(ChurnRiskPrediction, prediction_id)

    def find_matching_batch(
        self,
        db: Session,
        *,
        model_sha256: str,
        source_sha256: str,
        source_system: str,
    ) -> ChurnScoringBatch | None:
        return db.scalar(
            select(ChurnScoringBatch).where(
                ChurnScoringBatch.model_artifact_sha256 == model_sha256,
                ChurnScoringBatch.source_sha256 == source_sha256,
                ChurnScoringBatch.source_system == source_system,
            )
        )

    def latest_completed_before(
        self, db: Session, batch_id: int, model_sha256: str
    ) -> ChurnScoringBatch | None:
        return db.scalar(
            select(ChurnScoringBatch)
            .where(
                ChurnScoringBatch.id != batch_id,
                ChurnScoringBatch.model_artifact_sha256 == model_sha256,
                ChurnScoringBatch.status == "completed",
            )
            .order_by(ChurnScoringBatch.finished_at.desc(), ChurnScoringBatch.id.desc())
        )

    def list_batches(
        self,
        db: Session,
        *,
        start: datetime,
        end: datetime,
        status: str | None,
        limit: int,
    ) -> tuple[list[ChurnScoringBatch], int]:
        filters = [
            ChurnScoringBatch.created_at >= start,
            ChurnScoringBatch.created_at <= end,
        ]
        if status is not None:
            filters.append(ChurnScoringBatch.status == status)
        total = int(
            db.scalar(select(func.count(ChurnScoringBatch.id)).where(*filters)) or 0
        )
        items = list(
            db.scalars(
                select(ChurnScoringBatch)
                .where(*filters)
                .order_by(ChurnScoringBatch.created_at.desc(), ChurnScoringBatch.id.desc())
                .limit(limit)
            ).all()
        )
        return items, total

    def add_predictions(self, db: Session, predictions: list[ChurnRiskPrediction]) -> None:
        db.add_all(predictions)

    def list_predictions(
        self,
        db: Session,
        batch_id: int,
        *,
        risk_level: str | None = None,
        keyword: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[ChurnRiskPrediction], int]:
        filters = [ChurnRiskPrediction.batch_id == batch_id]
        if risk_level is not None:
            filters.append(ChurnRiskPrediction.risk_level == risk_level)
        if keyword:
            filters.append(ChurnRiskPrediction.student_external_id.contains(keyword, autoescape=True))
        total = int(
            db.scalar(select(func.count(ChurnRiskPrediction.id)).where(*filters)) or 0
        )
        items = list(
            db.scalars(
                select(ChurnRiskPrediction)
                .where(*filters)
                .order_by(ChurnRiskPrediction.risk_rank)
                .offset((page - 1) * page_size)
                .limit(page_size)
            ).all()
        )
        return items, total

    def list_prediction_rows(
        self,
        db: Session,
        batch_id: int,
        *,
        customer_filters: list,
        include_unmapped: bool,
        risk_level: str | None = None,
        keyword: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[tuple], int]:
        joins = (
            ChurnRiskPrediction.__table__
            .outerjoin(ExternalStudentMapping, ChurnRiskPrediction.mapping_id == ExternalStudentMapping.id)
            .outerjoin(Student, ExternalStudentMapping.student_id == Student.id)
            .outerjoin(Customer, Student.customer_id == Customer.id)
            .outerjoin(ChurnRiskIntervention, ChurnRiskIntervention.prediction_id == ChurnRiskPrediction.id)
        )
        filters = [ChurnRiskPrediction.batch_id == batch_id]
        if not include_unmapped:
            filters.append(Customer.id.is_not(None))
        filters.extend(customer_filters)
        if risk_level is not None:
            filters.append(ChurnRiskPrediction.risk_level == risk_level)
        if keyword:
            filters.append(ChurnRiskPrediction.student_external_id.contains(keyword, autoescape=True))
        statement = (
            select(
                ChurnRiskPrediction,
                ExternalStudentMapping,
                Student,
                Customer,
                ChurnRiskIntervention,
            )
            .select_from(joins)
            .where(*filters)
        )
        total = int(db.scalar(select(func.count()).select_from(statement.subquery())) or 0)
        rows = list(
            db.execute(
                statement.order_by(ChurnRiskPrediction.risk_rank)
                .offset((page - 1) * page_size)
                .limit(page_size)
            ).all()
        )
        return rows, total

    def scoped_risk_counts(
        self,
        db: Session,
        batch_id: int,
        *,
        customer_filters: list,
        include_unmapped: bool,
    ) -> dict[str, int]:
        joins = (
            ChurnRiskPrediction.__table__
            .outerjoin(ExternalStudentMapping, ChurnRiskPrediction.mapping_id == ExternalStudentMapping.id)
            .outerjoin(Student, ExternalStudentMapping.student_id == Student.id)
            .outerjoin(Customer, Student.customer_id == Customer.id)
        )
        filters = [ChurnRiskPrediction.batch_id == batch_id, *customer_filters]
        if not include_unmapped:
            filters.append(Customer.id.is_not(None))
        rows = db.execute(
            select(ChurnRiskPrediction.risk_level, func.count(ChurnRiskPrediction.id))
            .select_from(joins)
            .where(*filters)
            .group_by(ChurnRiskPrediction.risk_level)
        ).all()
        counts = {"high": 0, "medium": 0, "low": 0}
        for level, count in rows:
            counts[str(level)] = int(count)
        return counts

    def delete_batches_before(self, db: Session, cutoff: datetime) -> int:
        result = db.execute(delete(ChurnScoringBatch).where(ChurnScoringBatch.created_at < cutoff))
        return int(result.rowcount or 0)

    def list_top_predictions(
        self,
        db: Session,
        batch_id: int,
        *,
        limit: int = 10,
    ) -> list[ChurnRiskPrediction]:
        return list(
            db.scalars(
                select(ChurnRiskPrediction)
                .where(ChurnRiskPrediction.batch_id == batch_id)
                .order_by(ChurnRiskPrediction.risk_rank)
                .limit(limit)
            ).all()
        )
