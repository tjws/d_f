"""外部学生映射的数据访问层。"""

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.churn_risk_prediction import ChurnRiskPrediction
from app.models.churn_scoring_batch import ChurnScoringBatch
from app.models.external_student_mapping import ExternalStudentMapping


class ExternalStudentMappingDAO:
    def list_by_external_ids(
        self, db: Session, source_system: str, external_student_ids: list[str]
    ) -> dict[str, ExternalStudentMapping]:
        if not external_student_ids:
            return {}
        items = db.scalars(
            select(ExternalStudentMapping).where(
                ExternalStudentMapping.source_system == source_system,
                ExternalStudentMapping.external_student_id.in_(external_student_ids),
            )
        ).all()
        return {item.external_student_id: item for item in items}

    def get_by_external_id(
        self, db: Session, source_system: str, external_student_id: str
    ) -> ExternalStudentMapping | None:
        return db.scalar(
            select(ExternalStudentMapping).where(
                ExternalStudentMapping.source_system == source_system,
                ExternalStudentMapping.external_student_id == external_student_id,
            )
        )

    def add(self, db: Session, mapping: ExternalStudentMapping) -> None:
        db.add(mapping)

    def bind_existing_predictions(self, db: Session, mapping: ExternalStudentMapping) -> int:
        """映射补录后回填历史未映射预测，但不覆盖既有历史映射。"""

        result = db.execute(
            update(ChurnRiskPrediction)
            .where(
                ChurnRiskPrediction.mapping_id.is_(None),
                ChurnRiskPrediction.student_external_id == mapping.external_student_id,
                ChurnRiskPrediction.batch_id.in_(
                    select(ChurnScoringBatch.id).where(
                        ChurnScoringBatch.source_system == mapping.source_system
                    )
                ),
            )
            .values(mapping_id=mapping.id)
        )
        return int(result.rowcount or 0)
