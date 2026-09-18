from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.student import Student


class StudentDAO:
    def add(self, db: Session, student: Student) -> None:
        db.add(student)

    def list_by_customer(self, db: Session, customer_id: int, include_archived: bool = False) -> list[Student]:
        query = select(Student).where(Student.customer_id == customer_id)
        if not include_archived:
            query = query.where(Student.archived_at.is_(None))
        return list(db.scalars(query.order_by(Student.id)).all())

    def get_by_id(self, db: Session, customer_id: int, student_id: int) -> Student | None:
        return db.scalar(select(Student).where(Student.customer_id == customer_id, Student.id == student_id))

    def archive(self, student: Student, archived_at: datetime) -> None:
        student.archived_at = archived_at

    def restore(self, student: Student) -> None:
        student.archived_at = None
