from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.crypto import decrypt_text, encrypt_text
from app.dao.student_dao import StudentDAO
from app.models.student import Student
from app.models.user import User
from app.schemas.student import StudentCreate, StudentRead, StudentUpdate
from app.services.customer_service import get_customer_or_404


student_dao = StudentDAO()


def to_student_read(student: Student) -> StudentRead:
    return StudentRead(id=student.id, customer_id=student.customer_id, name=decrypt_text(student.name_encrypted), gender=student.gender, grade=student.grade, school=decrypt_text(student.school_encrypted) if student.school_encrypted else None, birth_date=student.birth_date, subjects=student.subjects_json, created_at=student.created_at, updated_at=student.updated_at, archived_at=student.archived_at)


def create_student(db: Session, customer_id: int, current_user: User, payload: StudentCreate) -> Student:
    # 学生资料会影响客户全貌，因此沿用客户 update 数据范围。
    get_customer_or_404(db, customer_id, current_user, "update")
    student = Student(customer_id=customer_id, name_encrypted=encrypt_text(payload.name), gender=payload.gender, grade=payload.grade, school_encrypted=encrypt_text(payload.school) if payload.school else None, birth_date=payload.birth_date, subjects_json=payload.subjects)
    student_dao.add(db, student)
    db.commit()
    db.refresh(student)
    return student


def list_students(db: Session, customer_id: int, current_user: User, include_archived: bool = False) -> list[Student]:
    get_customer_or_404(db, customer_id, current_user, "read")
    return student_dao.list_by_customer(db, customer_id, include_archived=include_archived)


def update_student(db: Session, customer_id: int, student_id: int, current_user: User, payload: StudentUpdate) -> Student:
    get_customer_or_404(db, customer_id, current_user, "update")
    student = student_dao.get_by_id(db, customer_id, student_id)
    if student is None or student.archived_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="学生不存在")
    values = payload.model_dump(exclude_unset=True)
    if "name" in values and values["name"] is not None:
        student.name_encrypted = encrypt_text(values.pop("name"))
    if "school" in values:
        school = values.pop("school")
        student.school_encrypted = encrypt_text(school) if school else None
    for key, value in values.items():
        setattr(student, "subjects_json" if key == "subjects" else key, value)
    db.commit()
    db.refresh(student)
    return student


def archive_student(db: Session, customer_id: int, student_id: int, current_user: User) -> Student:
    get_customer_or_404(db, customer_id, current_user, "update")
    student = student_dao.get_by_id(db, customer_id, student_id)
    if student is None or student.archived_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="学生不存在")
    student_dao.archive(student, datetime.now(timezone.utc))
    db.commit()
    db.refresh(student)
    return student


def restore_student(db: Session, customer_id: int, student_id: int, current_user: User) -> Student:
    get_customer_or_404(db, customer_id, current_user, "update")
    student = student_dao.get_by_id(db, customer_id, student_id)
    if student is None or student.archived_at is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="归档学生不存在")
    student_dao.restore(student)
    db.commit()
    db.refresh(student)
    return student
