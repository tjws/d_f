from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.student import StudentCreate, StudentRead, StudentUpdate
from app.services.student_service import archive_student, create_student as create_student_service, list_students as list_students_service, restore_student, to_student_read, update_student

router = APIRouter(prefix="/customers/{customer_id}/students", tags=["students"])


@router.post("", response_model=StudentRead, status_code=status.HTTP_201_CREATED)
def create_student(customer_id: int, payload: StudentCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return to_student_read(create_student_service(db, customer_id, current_user, payload))


@router.get("", response_model=list[StudentRead])
def list_students(customer_id: int, include_archived: bool = Query(default=False), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return [to_student_read(student) for student in list_students_service(db, customer_id, current_user, include_archived=include_archived)]


@router.patch("/{student_id}", response_model=StudentRead)
def edit_student(customer_id: int, student_id: int, payload: StudentUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return to_student_read(update_student(db, customer_id, student_id, current_user, payload))


@router.post("/{student_id}/archive", response_model=StudentRead)
def archive_student_route(customer_id: int, student_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return to_student_read(archive_student(db, customer_id, student_id, current_user))


@router.post("/{student_id}/restore", response_model=StudentRead)
def restore_student_route(customer_id: int, student_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return to_student_read(restore_student(db, customer_id, student_id, current_user))
