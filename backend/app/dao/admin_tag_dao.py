from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.customer_tag import CustomerTag
from app.models.tag import Tag


class AdminTagDAO:
    """读取标签目录及其客户使用情况；统计口径由 Service 负责解释。"""

    def list_with_assignments(self, db: Session) -> tuple[list[Tag], list[CustomerTag]]:
        tags = list(db.scalars(select(Tag).order_by(Tag.category, Tag.name, Tag.id)).all())
        assignments = list(db.scalars(select(CustomerTag)).all())
        return tags, assignments

    def get_by_id(self, db: Session, tag_id: int) -> Tag | None:
        return db.get(Tag, tag_id)

    def get_by_key(self, db: Session, key: str) -> Tag | None:
        return db.scalar(select(Tag).where(Tag.key == key))

    def add(self, db: Session, tag: Tag) -> None:
        db.add(tag)
