from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.user import User


class UserDAO:
    """员工用户的持久化操作；这里不调用 commit 或 rollback。"""

    def get_by_id(self, db: Session, user_id: int) -> User | None:
        return db.get(User, user_id)

    def get_by_username(self, db: Session, username: str) -> User | None:
        return db.scalar(select(User).where(User.username == username))

    def get_by_wecom_userid(self, db: Session, userid: str) -> User | None:
        return db.scalar(select(User).where(User.wecom_userid == userid))

    def list_all(self, db: Session) -> list[User]:
        return list(db.scalars(select(User).order_by(User.id)).all())

    def count_active_admins(self, db: Session) -> int:
        return db.scalar(select(func.count(User.id)).where(User.role == "admin", User.is_active.is_(True))) or 0

    def add(self, db: Session, user: User) -> None:
        db.add(user)
