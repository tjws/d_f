from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.tag import Tag


class TagDAO:
    def get_by_key(self, db: Session, key: str) -> Tag | None:
        return db.scalar(select(Tag).where(Tag.key == key))

    def list_active(self, db: Session) -> list[Tag]:
        return list(db.scalars(select(Tag).where(Tag.status == "active").order_by(Tag.category, Tag.id)).all())

    def add(self, db: Session, tag: Tag) -> None:
        db.add(tag)
