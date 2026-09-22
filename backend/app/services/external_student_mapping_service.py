"""外部学生编号映射业务。"""

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.dao.external_student_mapping_dao import ExternalStudentMappingDAO
from app.dao.student_dao import StudentDAO
from app.models.external_student_mapping import ExternalStudentMapping
from app.models.user import User
from app.schemas.churn_risk import ExternalStudentMappingCreate
from app.services.audit_log_service import append_audit_log
from app.services.customer_service import get_customer_or_404


mapping_dao = ExternalStudentMappingDAO()
student_dao = StudentDAO()


def create_external_student_mapping(
    db: Session, current_user: User, payload: ExternalStudentMappingCreate
) -> dict[str, object]:
    source_system = payload.source_system.strip().lower()
    external_id = payload.external_student_id.strip()
    if not source_system or not external_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="外部系统和学生编号不能为空",
        )

    student = student_dao.get_any_by_id(db, payload.student_id)
    if student is None or student.archived_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="学生不存在")
    # 映射会决定风险记录可见范围，所以必须先验证操作者能更新对应客户。
    get_customer_or_404(db, student.customer_id, current_user, "update")

    existing = mapping_dao.get_by_external_id(db, source_system, external_id)
    if existing is not None:
        if existing.student_id != student.id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="该外部学生编号已经映射到其他学生",
            )
        rebound = mapping_dao.bind_existing_predictions(db, existing)
        db.commit()
        return _mapping_read(existing, student.customer_id, rebound)

    mapping = ExternalStudentMapping(
        source_system=source_system,
        external_student_id=external_id,
        student_id=student.id,
        created_by=current_user.id,
    )
    mapping_dao.add(db, mapping)
    db.flush()
    rebound = mapping_dao.bind_existing_predictions(db, mapping)
    append_audit_log(
        db,
        current_user,
        "churn.student_mapping_created",
        "external_student_mapping",
        str(mapping.id),
        {
            "source_system": source_system,
            "student_id": student.id,
            "customer_id": student.customer_id,
            "rebound_prediction_count": rebound,
        },
    )
    db.commit()
    db.refresh(mapping)
    return _mapping_read(mapping, student.customer_id, rebound)


def _mapping_read(
    mapping: ExternalStudentMapping, customer_id: int, rebound: int
) -> dict[str, object]:
    return {
        "id": mapping.id,
        "source_system": mapping.source_system,
        "external_student_id": mapping.external_student_id,
        "student_id": mapping.student_id,
        "customer_id": customer_id,
        "rebound_prediction_count": rebound,
        "created_at": mapping.created_at,
    }
