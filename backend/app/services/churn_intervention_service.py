"""流失风险人工干预闭环。"""

from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.crypto import decrypt_text, encrypt_text
from app.dao.churn_intervention_dao import ChurnInterventionDAO
from app.dao.churn_risk_dao import ChurnRiskDAO
from app.dao.schedule_dao import ScheduleDAO
from app.dao.timeline_event_dao import TimelineEventDAO
from app.models.churn_risk_intervention import ChurnRiskIntervention
from app.models.external_student_mapping import ExternalStudentMapping
from app.models.schedule import Schedule
from app.models.student import Student
from app.models.timeline_event import TimelineEvent
from app.models.user import User
from app.schemas.churn_risk import ChurnInterventionCreate, ChurnInterventionUpdate
from app.services.audit_log_service import append_audit_log
from app.services.customer_service import get_customer_or_404


intervention_dao = ChurnInterventionDAO()
risk_dao = ChurnRiskDAO()
schedule_dao = ScheduleDAO()
timeline_dao = TimelineEventDAO()

_ALLOWED_TRANSITIONS = {
    "planned": {"in_progress", "completed", "cancelled"},
    "in_progress": {"completed", "cancelled"},
    "completed": set(),
    "cancelled": set(),
}
_OUTCOME_TO_SCHEDULE = {
    "retained": "contacted",
    "recovered": "converted",
    "churned": "lost",
    "unknown": "other",
}


def create_churn_intervention(
    db: Session,
    prediction_id: int,
    current_user: User,
    payload: ChurnInterventionCreate,
) -> dict[str, object]:
    prediction = risk_dao.get_prediction(db, prediction_id)
    if prediction is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="流失风险记录不存在")
    if prediction.mapping_id is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="请先把外部学生编号映射到系统学生",
        )
    mapping = db.get(ExternalStudentMapping, prediction.mapping_id)
    student = db.get(Student, mapping.student_id) if mapping is not None else None
    if student is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="风险记录的学生映射已失效")
    get_customer_or_404(db, student.customer_id, current_user, "update")

    existing = intervention_dao.get_by_prediction(db, prediction_id)
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="该风险记录已有人工干预")
    due_at = _as_utc(payload.due_at)
    note = payload.note.strip() if payload.note else None

    schedule = Schedule(
        customer_id=student.customer_id,
        user_id=current_user.id,
        suggestion_id=None,
        title="客户流失风险人工跟进",
        description=f"风险等级：{prediction.risk_level}；方式：{payload.action_type}",
        due_at=due_at,
        priority="high" if prediction.risk_level == "high" else "normal",
        source="churn",
        status="confirmed",
        evidence_json=[
            {
                "type": "churn_risk_prediction",
                "id": prediction.id,
                "batch_id": prediction.batch_id,
                "risk_level": prediction.risk_level,
            }
        ],
        confirmed_by=current_user.id,
        confirmed_at=datetime.now(timezone.utc),
    )
    schedule_dao.add(db, schedule)
    db.flush()

    intervention = ChurnRiskIntervention(
        prediction_id=prediction.id,
        customer_id=student.customer_id,
        student_id=student.id,
        actor_user_id=current_user.id,
        schedule_id=schedule.id,
        action_type=payload.action_type,
        status="planned",
        note_encrypted=encrypt_text(note) if note else None,
        due_at=due_at,
    )
    intervention_dao.add(db, intervention)
    db.flush()
    timeline_dao.add(
        db,
        TimelineEvent(
            customer_id=student.customer_id,
            operator_id=current_user.id,
            occurred_at=datetime.now(timezone.utc),
            event_type="churn_intervention_created",
            summary_encrypted=encrypt_text(
                f"已为{prediction.risk_level}流失风险创建人工跟进任务"
            ),
            source="system",
            reference_type="churn_intervention",
            reference_id=str(intervention.id),
        ),
    )
    append_audit_log(
        db,
        current_user,
        "churn.intervention_created",
        "churn_risk_intervention",
        str(intervention.id),
        {"prediction_id": prediction.id, "customer_id": student.customer_id, "status": "planned"},
    )
    db.commit()
    db.refresh(intervention)
    return intervention_read(intervention)


def update_churn_intervention(
    db: Session,
    intervention_id: int,
    current_user: User,
    payload: ChurnInterventionUpdate,
) -> dict[str, object]:
    intervention = intervention_dao.get_by_id(db, intervention_id)
    if intervention is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="流失干预记录不存在")
    get_customer_or_404(db, intervention.customer_id, current_user, "update")
    if payload.status == intervention.status:
        return intervention_read(intervention)
    if payload.status not in _ALLOWED_TRANSITIONS.get(intervention.status, set()):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="当前状态不允许该流转")
    if payload.status == "completed" and payload.outcome is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="完成干预时必须填写结果")

    now = datetime.now(timezone.utc)
    note = payload.note.strip() if payload.note else None
    intervention.status = payload.status
    intervention.outcome = payload.outcome
    if note is not None:
        intervention.note_encrypted = encrypt_text(note)
    schedule = db.get(Schedule, intervention.schedule_id) if intervention.schedule_id else None
    if payload.status == "completed":
        intervention.completed_at = now
        if schedule is not None:
            schedule.status = "completed"
            schedule.outcome = _OUTCOME_TO_SCHEDULE[payload.outcome]
            schedule.completed_at = now
    elif payload.status == "cancelled" and schedule is not None:
        schedule.status = "cancelled"

    timeline_dao.add(
        db,
        TimelineEvent(
            customer_id=intervention.customer_id,
            operator_id=current_user.id,
            occurred_at=now,
            event_type=f"churn_intervention_{payload.status}",
            summary_encrypted=encrypt_text(
                f"流失风险人工干预更新为{payload.status}"
                + (f"，结果为{payload.outcome}" if payload.outcome else "")
            ),
            source="manual",
            reference_type="churn_intervention",
            reference_id=str(intervention.id),
        ),
    )
    append_audit_log(
        db,
        current_user,
        "churn.intervention_updated",
        "churn_risk_intervention",
        str(intervention.id),
        {"status": payload.status, "outcome": payload.outcome},
    )
    db.commit()
    db.refresh(intervention)
    return intervention_read(intervention)


def intervention_read(intervention: ChurnRiskIntervention) -> dict[str, object]:
    return {
        "id": intervention.id,
        "prediction_id": intervention.prediction_id,
        "customer_id": intervention.customer_id,
        "student_id": intervention.student_id,
        "actor_user_id": intervention.actor_user_id,
        "schedule_id": intervention.schedule_id,
        "action_type": intervention.action_type,
        "status": intervention.status,
        "outcome": intervention.outcome,
        "note": decrypt_text(intervention.note_encrypted) if intervention.note_encrypted else None,
        "due_at": intervention.due_at,
        "completed_at": intervention.completed_at,
        "created_at": intervention.created_at,
        "updated_at": intervention.updated_at,
    }


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
