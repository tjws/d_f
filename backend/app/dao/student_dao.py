from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.student import Student


class StudentDAO:
    def add(self, db: Session, student: Student) -> None:
        db.add(student)

    def list_by_customer(self, db: Session, customer_id: int) -> list[Student]:
        return list(db.scalars(select(Student).where(Student.customer_id == customer_id).order_by(Student.id)).all())
