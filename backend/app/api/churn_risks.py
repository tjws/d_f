"""客户流失风险查询、人工干预与模型治理接口。"""

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, require_roles
from app.db.session import get_db
from app.models.user import User
from app.schemas.churn_risk import (
    ChurnInterventionCreate,
    ChurnInterventionRead,
    ChurnInterventionUpdate,
    ChurnRiskBatchDetail,
    ChurnModelRegister,
    ChurnModelVersionRead,
    ChurnScoringAccepted,
    ChurnScoringRequest,
    ChurnScoringBatchList,
    ExternalStudentMappingCreate,
    ExternalStudentMappingRead,
)
from app.services.churn_intervention_service import (
    create_churn_intervention,
    update_churn_intervention,
)
from app.services.external_student_mapping_service import create_external_student_mapping
from app.services.churn_model_governance_service import (
    approve_churn_model,
    list_churn_models,
    register_churn_model,
    request_churn_scoring,
)
from app.services.churn_risk_admin_service import (
    get_churn_batch_detail,
    list_churn_scoring_batches,
)


router = APIRouter(prefix="/admin/churn-risks", tags=["churn-risks"])


@router.get("/batches", response_model=ChurnScoringBatchList)
def read_churn_scoring_batches(
    start: datetime | None = Query(default=None),
    end: datetime | None = Query(default=None),
    batch_status: str | None = Query(default=None, alias="status", max_length=20),
    limit: int = Query(default=50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return list_churn_scoring_batches(
        db,
        start=start,
        end=end,
        batch_status=batch_status,
        limit=limit,
        current_user=current_user,
    )


@router.get("/batches/{batch_id}", response_model=ChurnRiskBatchDetail)
def read_churn_scoring_batch(
    batch_id: int,
    risk_level: str | None = Query(default=None, max_length=20),
    keyword: str | None = Query(default=None, max_length=100),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_churn_batch_detail(
        db,
        batch_id=batch_id,
        risk_level=risk_level,
        keyword=keyword,
        page=page,
        page_size=page_size,
        current_user=current_user,
    )


@router.post(
    "/mappings",
    response_model=ExternalStudentMappingRead,
    status_code=201,
)
def create_student_mapping(
    payload: ExternalStudentMappingCreate,
    current_user: User = Depends(require_roles("admin", "manager")),
    db: Session = Depends(get_db),
):
    return create_external_student_mapping(db, current_user, payload)


@router.post(
    "/predictions/{prediction_id}/intervention",
    response_model=ChurnInterventionRead,
    status_code=201,
)
def create_intervention(
    prediction_id: int,
    payload: ChurnInterventionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return create_churn_intervention(db, prediction_id, current_user, payload)


@router.patch(
    "/interventions/{intervention_id}",
    response_model=ChurnInterventionRead,
)
def update_intervention(
    intervention_id: int,
    payload: ChurnInterventionUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return update_churn_intervention(db, intervention_id, current_user, payload)


@router.get("/models", response_model=list[ChurnModelVersionRead])
def read_models(
    current_user: User = Depends(require_roles("admin", "manager")),
    db: Session = Depends(get_db),
):
    del current_user
    return list_churn_models(db)


@router.post("/models", response_model=ChurnModelVersionRead, status_code=201)
def register_model(
    payload: ChurnModelRegister,
    current_user: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    return register_churn_model(db, current_user, payload)


@router.post("/models/{model_id}/approve", response_model=ChurnModelVersionRead)
def approve_model(
    model_id: int,
    current_user: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    return approve_churn_model(db, current_user, model_id)


@router.post("/score", response_model=ChurnScoringAccepted, status_code=202)
def score_import_file(
    payload: ChurnScoringRequest,
    current_user: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    return request_churn_scoring(db, current_user, payload)
