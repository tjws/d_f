from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.student import StudentCreate, StudentRead
from app.services.student_service import create_student as create_student_service, list_students as list_students_service, to_student_read

router = APIRouter(prefix="/customers/{customer_id}/students", tags=["students"])


@router.post("", response_model=StudentRead, status_code=status.HTTP_201_CREATED)
def create_student(customer_id: int, payload: StudentCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return to_student_read(create_student_service(db, customer_id, current_user, payload))


@router.get("", response_model=list[StudentRead])
def list_students(customer_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return [to_student_read(student) for student in list_students_service(db, customer_id, current_user)]
