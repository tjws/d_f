from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.sales_script import SalesScript


class SalesScriptDAO:
    def get_by_id(self, db: Session, script_id: int) -> SalesScript | None:
        return db.get(SalesScript, script_id)

    def list_all(self, db: Session) -> list[SalesScript]:
        return list(db.scalars(select(SalesScript).order_by(SalesScript.updated_at.desc(), SalesScript.id.desc())).all())

    def search_published(self, db: Session, query: str, limit: int = 4) -> list[SalesScript]:
        pattern = f"%{query.strip()}%"
        statement = select(SalesScript).where(SalesScript.status == "published", or_(SalesScript.title.ilike(pattern), SalesScript.content.ilike(pattern), SalesScript.scene.ilike(pattern))).order_by(SalesScript.updated_at.desc(), SalesScript.id.desc()).limit(limit)
        return list(db.scalars(statement).all())

    def add(self, db: Session, script: SalesScript) -> None:
        db.add(script)
