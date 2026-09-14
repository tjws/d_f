from sqlalchemy.orm import Session

from app.core.crypto import decrypt_text, encrypt_text
from app.dao.student_dao import StudentDAO
from app.models.student import Student
from app.models.user import User
from app.schemas.student import StudentCreate, StudentRead
from app.services.customer_service import get_customer_or_404


student_dao = StudentDAO()


def to_student_read(student: Student) -> StudentRead:
    return StudentRead(id=student.id, customer_id=student.customer_id, name=decrypt_text(student.name_encrypted), gender=student.gender, grade=student.grade, school=decrypt_text(student.school_encrypted) if student.school_encrypted else None, birth_date=student.birth_date, subjects=student.subjects_json, created_at=student.created_at, updated_at=student.updated_at)


def create_student(db: Session, customer_id: int, current_user: User, payload: StudentCreate) -> Student:
    # 学生资料会影响客户全貌，因此沿用客户 update 数据范围。
    get_customer_or_404(db, customer_id, current_user, "update")
    student = Student(customer_id=customer_id, name_encrypted=encrypt_text(payload.name), gender=payload.gender, grade=payload.grade, school_encrypted=encrypt_text(payload.school) if payload.school else None, birth_date=payload.birth_date, subjects_json=payload.subjects)
    student_dao.add(db, student)
    db.commit()
    db.refresh(student)
    return student


def list_students(db: Session, customer_id: int, current_user: User) -> list[Student]:
    get_customer_or_404(db, customer_id, current_user, "read")
    return student_dao.list_by_customer(db, customer_id)
