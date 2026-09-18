from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.course_order import CourseOrderCreate, CourseOrderRead, CourseOrderUpdate
from app.services.course_order_service import create_order, list_orders, to_order_read, update_order


router = APIRouter(prefix="/customers/{customer_id}/orders", tags=["course-orders"])


@router.post("", response_model=CourseOrderRead, status_code=status.HTTP_201_CREATED)
def create_course_order(customer_id: int, payload: CourseOrderCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return to_order_read(create_order(db, customer_id, current_user, payload))


@router.get("", response_model=list[CourseOrderRead])
def get_course_orders(customer_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return [to_order_read(order) for order in list_orders(db, customer_id, current_user)]


@router.patch("/{order_id}", response_model=CourseOrderRead)
def edit_course_order(customer_id: int, order_id: int, payload: CourseOrderUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return to_order_read(update_order(db, customer_id, order_id, current_user, payload))
