"""客户流失风险查询与数据范围服务。"""

from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.dao.churn_risk_dao import ChurnRiskDAO
from app.models.churn_risk_prediction import ChurnRiskPrediction
from app.models.churn_scoring_batch import ChurnScoringBatch
from app.models.user import User
from app.services.churn_intervention_service import intervention_read
from app.services.customer_service import customer_scope_filters


churn_risk_dao = ChurnRiskDAO()
_BATCH_STATUSES = {"running", "completed", "failed"}
_RISK_LEVELS = {"high", "medium", "low"}


def _batch_read(
    batch: ChurnScoringBatch, counts: dict[str, int] | None = None
) -> dict[str, object]:
    resolved_counts = counts or {
        "high": batch.high_count,
        "medium": batch.medium_count,
        "low": batch.low_count,
    }
    return {
        "id": batch.id,
        "status": batch.status,
        "model_name": batch.model_name,
        "model_schema_version": batch.model_schema_version,
        "model_version_id": batch.model_version_id,
        "source_filename": batch.source_filename,
        "source_sha256": batch.source_sha256,
        "source_system": batch.source_system,
        "trigger_source": batch.trigger_source,
        "observation_at": batch.observation_at,
        "decision_threshold": batch.decision_threshold,
        "medium_threshold": batch.medium_threshold,
        "row_count": batch.row_count,
        "scored_count": sum(resolved_counts.values()),
        "high_count": resolved_counts["high"],
        "medium_count": resolved_counts["medium"],
        "low_count": resolved_counts["low"],
        "error_code": batch.error_code,
        "drift_status": batch.drift_status,
        "drift": batch.drift_json,
        "started_at": batch.started_at,
        "finished_at": batch.finished_at,
        "created_at": batch.created_at,
    }


def _prediction_read(row: tuple) -> dict[str, object]:
    prediction, mapping, student, customer, intervention = row
    return {
        "id": prediction.id,
        "student_external_id": prediction.student_external_id,
        "risk_score": prediction.risk_probability,
        "risk_level": prediction.risk_level,
        "predicted_churn": prediction.predicted_churn,
        "risk_rank": prediction.risk_rank,
        "risk_percentile": prediction.risk_percentile,
        "mapping_id": mapping.id if mapping is not None else None,
        "student_id": student.id if student is not None else None,
        "customer_id": customer.id if customer is not None else None,
        "customer_name": customer.name if customer is not None else None,
        "owner_id": customer.owner_id if customer is not None else None,
        "mapping_status": "mapped" if customer is not None else "unmapped",
        "intervention": intervention_read(intervention) if intervention is not None else None,
        "created_at": prediction.created_at,
    }


def list_churn_scoring_batches(
    db: Session,
    *,
    start: datetime | None,
    end: datetime | None,
    batch_status: str | None,
    limit: int,
    current_user: User,
) -> dict[str, object]:
    end_at = end or datetime.now(timezone.utc)
    start_at = start or (end_at - timedelta(days=30))
    if end_at <= start_at or (end_at - start_at) > timedelta(days=366):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="评分批次时间范围必须在 0 到 366 天内",
        )
    if batch_status is not None and batch_status not in _BATCH_STATUSES:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="不支持的批次状态")
    items, total = churn_risk_dao.list_batches(
        db,
        start=start_at,
        end=end_at,
        status=batch_status,
        limit=limit,
    )
    filters = customer_scope_filters(db, current_user, "read")
    include_unmapped = current_user.role == "admin"
    visible: list[dict[str, object]] = []
    for item in items:
        counts = churn_risk_dao.scoped_risk_counts(
            db,
            item.id,
            customer_filters=filters,
            include_unmapped=include_unmapped,
        )
        if current_user.role == "admin" or sum(counts.values()) > 0:
            visible.append(_batch_read(item, counts))
    return {"items": visible, "total": len(visible) if current_user.role != "admin" else total}


def get_churn_batch_detail(
    db: Session,
    *,
    batch_id: int,
    risk_level: str | None,
    keyword: str | None,
    page: int,
    page_size: int,
    current_user: User,
) -> dict[str, object]:
    batch = churn_risk_dao.get_batch(db, batch_id)
    if batch is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="客户流失评分批次不存在")
    if risk_level is not None and risk_level not in _RISK_LEVELS:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="不支持的风险等级")
    normalized_keyword = keyword.strip() if keyword else None
    customer_filters = customer_scope_filters(db, current_user, "read")
    include_unmapped = current_user.role == "admin"
    items, total = churn_risk_dao.list_prediction_rows(
        db,
        batch_id,
        customer_filters=customer_filters,
        include_unmapped=include_unmapped,
        risk_level=risk_level,
        keyword=normalized_keyword,
        page=page,
        page_size=page_size,
    )
    return {
        "batch": _batch_read(
            batch,
            churn_risk_dao.scoped_risk_counts(
                db,
                batch.id,
                customer_filters=customer_filters,
                include_unmapped=include_unmapped,
            ),
        ),
        "items": [_prediction_read(item) for item in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }
