"""流失干预记录的数据访问层。"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.churn_risk_intervention import ChurnRiskIntervention


class ChurnInterventionDAO:
    def add(self, db: Session, intervention: ChurnRiskIntervention) -> None:
        db.add(intervention)

    def get_by_prediction(
        self, db: Session, prediction_id: int
    ) -> ChurnRiskIntervention | None:
        return db.scalar(
            select(ChurnRiskIntervention).where(
                ChurnRiskIntervention.prediction_id == prediction_id
            )
        )

    def get_by_id(self, db: Session, intervention_id: int) -> ChurnRiskIntervention | None:
        return db.get(ChurnRiskIntervention, intervention_id)
