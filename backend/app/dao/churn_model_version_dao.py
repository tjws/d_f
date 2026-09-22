"""流失模型版本的数据访问层。"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.churn_model_version import ChurnModelVersion


class ChurnModelVersionDAO:
    def add(self, db: Session, model: ChurnModelVersion) -> None:
        db.add(model)

    def get_by_id(self, db: Session, model_id: int) -> ChurnModelVersion | None:
        return db.get(ChurnModelVersion, model_id)

    def get_by_sha256(self, db: Session, digest: str) -> ChurnModelVersion | None:
        return db.scalar(
            select(ChurnModelVersion).where(ChurnModelVersion.artifact_sha256 == digest)
        )

    def get_by_version(self, db: Session, version: str) -> ChurnModelVersion | None:
        return db.scalar(
            select(ChurnModelVersion).where(ChurnModelVersion.version == version)
        )

    def list_all(self, db: Session) -> list[ChurnModelVersion]:
        return list(
            db.scalars(
                select(ChurnModelVersion).order_by(
                    ChurnModelVersion.created_at.desc(), ChurnModelVersion.id.desc()
                )
            ).all()
        )

    def get_approved(self, db: Session) -> ChurnModelVersion | None:
        return db.scalar(
            select(ChurnModelVersion)
            .where(ChurnModelVersion.status == "approved")
            .order_by(ChurnModelVersion.approved_at.desc(), ChurnModelVersion.id.desc())
        )

    def list_approved(self, db: Session) -> list[ChurnModelVersion]:
        return list(
            db.scalars(
                select(ChurnModelVersion).where(ChurnModelVersion.status == "approved")
            ).all()
        )
