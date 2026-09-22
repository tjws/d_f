"""客户流失批量评分业务编排。"""

from dataclasses import dataclass
from datetime import datetime, timezone
import os
from pathlib import Path

from sqlalchemy.orm import Session

from app.churn.dataset import load_churn_scoring_csv
from app.churn.inference import load_churn_model, resolve_medium_threshold, score_students
from app.dao.churn_risk_dao import ChurnRiskDAO
from app.dao.external_student_mapping_dao import ExternalStudentMappingDAO
from app.models.churn_risk_prediction import ChurnRiskPrediction
from app.models.churn_scoring_batch import ChurnScoringBatch


churn_risk_dao = ChurnRiskDAO()
mapping_dao = ExternalStudentMappingDAO()


@dataclass(frozen=True)
class ChurnScoringSummary:
    batch_id: int
    status: str
    row_count: int
    scored_count: int
    high_count: int
    medium_count: int
    low_count: int
    decision_threshold: float
    medium_threshold: float
    top_risks: list[dict[str, object]]


def score_churn_csv_batch(
    db: Session,
    *,
    csv_path: str | Path,
    model_path: str | Path,
    medium_threshold: float | None = None,
    source_system: str = "csv",
    trigger_source: str = "manual",
    model_version_id: int | None = None,
    observation_at: datetime | None = None,
) -> ChurnScoringSummary:
    """读取可信模型和待评分 CSV，原子保存整批风险结果。

    批次先单独落库。后续预测或明细写入失败时，明细事务整体回滚，
    批次会被标记 failed，不会留下“部分成功”的风险名单。
    """

    frame, quality = load_churn_scoring_csv(csv_path)
    model = load_churn_model(model_path)
    resolved_medium_threshold = resolve_medium_threshold(model, medium_threshold)
    normalized_source = source_system.strip().lower()
    if not normalized_source:
        raise ValueError("source_system 不能为空")

    existing = churn_risk_dao.find_matching_batch(
        db,
        model_sha256=model.artifact_sha256,
        source_sha256=quality.source_sha256,
        source_system=normalized_source,
    )
    if existing is not None and existing.status == "completed":
        return _summary_from_batch(db, existing)
    if existing is not None and existing.status == "running":
        raise RuntimeError("相同模型和数据的评分任务正在运行")
    if existing is not None:
        # 失败批次保留同一个业务幂等键和批次号，允许人工重试。
        batch = existing
        batch.status = "running"
        batch.error_code = None
        batch.started_at = datetime.now(timezone.utc)
        batch.finished_at = None
        batch.trigger_source = trigger_source
        batch.observation_at = observation_at
    else:
        batch = ChurnScoringBatch(
            status="running",
            model_name=model.model_name,
            model_schema_version=model.schema_version,
            model_artifact_sha256=model.artifact_sha256,
            model_version_id=model_version_id,
            source_filename=quality.source_filename,
            source_sha256=quality.source_sha256,
            source_system=normalized_source,
            trigger_source=trigger_source,
            observation_at=observation_at,
            decision_threshold=model.decision_threshold,
            medium_threshold=resolved_medium_threshold,
            row_count=quality.row_count,
        )
        churn_risk_dao.add_batch(db, batch)
    db.commit()
    db.refresh(batch)
    batch_id = batch.id

    try:
        scored_students, _ = score_students(
            frame,
            model,
            medium_threshold=resolved_medium_threshold,
        )
        mapping_by_external_id = mapping_dao.list_by_external_ids(
            db,
            normalized_source,
            [item.student_external_id for item in scored_students],
        )
        predictions = [
            ChurnRiskPrediction(
                batch_id=batch_id,
                mapping_id=(
                    mapping_by_external_id[item.student_external_id].id
                    if item.student_external_id in mapping_by_external_id
                    else None
                ),
                student_external_id=item.student_external_id,
                risk_probability=item.risk_probability,
                risk_level=item.risk_level,
                predicted_churn=item.predicted_churn,
                risk_rank=item.risk_rank,
                risk_percentile=item.risk_percentile,
            )
            for item in scored_students
        ]
        churn_risk_dao.add_predictions(db, predictions)

        high_count = sum(item.risk_level == "high" for item in scored_students)
        medium_count = sum(item.risk_level == "medium" for item in scored_students)
        low_count = sum(item.risk_level == "low" for item in scored_students)
        batch.status = "completed"
        batch.scored_count = len(predictions)
        batch.high_count = high_count
        batch.medium_count = medium_count
        batch.low_count = low_count
        _set_distribution_drift(db, batch)
        batch.finished_at = datetime.now(timezone.utc)
        db.commit()
    except Exception as exc:
        db.rollback()
        failed_batch = churn_risk_dao.get_batch(db, batch_id)
        if failed_batch is not None:
            failed_batch.status = "failed"
            # 只记录错误类型，避免把本地路径、原始数据或模型内容写入数据库。
            failed_batch.error_code = type(exc).__name__[:80]
            failed_batch.finished_at = datetime.now(timezone.utc)
            db.commit()
        raise

    top_items = sorted(scored_students, key=lambda item: item.risk_rank)[:10]
    return ChurnScoringSummary(
        batch_id=batch_id,
        status="completed",
        row_count=quality.row_count,
        scored_count=len(scored_students),
        high_count=high_count,
        medium_count=medium_count,
        low_count=low_count,
        decision_threshold=model.decision_threshold,
        medium_threshold=resolved_medium_threshold,
        top_risks=[
            {
                "student_external_id": item.student_external_id,
                "risk_probability": round(item.risk_probability, 6),
                "risk_level": item.risk_level,
                "risk_rank": item.risk_rank,
            }
            for item in top_items
        ],
    )


def _summary_from_batch(db: Session, batch: ChurnScoringBatch) -> ChurnScoringSummary:
    top = churn_risk_dao.list_top_predictions(db, batch.id, limit=10)
    return ChurnScoringSummary(
        batch_id=batch.id,
        status="completed",
        row_count=batch.row_count,
        scored_count=batch.scored_count,
        high_count=batch.high_count,
        medium_count=batch.medium_count,
        low_count=batch.low_count,
        decision_threshold=batch.decision_threshold,
        medium_threshold=batch.medium_threshold,
        top_risks=[
            {
                "student_external_id": item.student_external_id,
                "risk_probability": round(item.risk_probability, 6),
                "risk_level": item.risk_level,
                "risk_rank": item.risk_rank,
            }
            for item in top
        ],
    )


def _set_distribution_drift(db: Session, batch: ChurnScoringBatch) -> None:
    """比较风险等级分布；这是运行监控，不冒充特征漂移或模型准确率。"""

    previous = churn_risk_dao.latest_completed_before(
        db, batch.id, batch.model_artifact_sha256
    )
    if previous is None or previous.scored_count <= 0 or batch.scored_count <= 0:
        batch.drift_status = "insufficient_history"
        batch.drift_json = {"metric": "risk_level_distribution", "previous_batch_id": None}
        return
    current = {
        "high": batch.high_count / batch.scored_count,
        "medium": batch.medium_count / batch.scored_count,
        "low": batch.low_count / batch.scored_count,
    }
    baseline = {
        "high": previous.high_count / previous.scored_count,
        "medium": previous.medium_count / previous.scored_count,
        "low": previous.low_count / previous.scored_count,
    }
    deltas = {key: round(abs(current[key] - baseline[key]), 6) for key in current}
    threshold = float(os.getenv("CHURN_DISTRIBUTION_DRIFT_THRESHOLD", "0.15"))
    batch.drift_status = "alert" if max(deltas.values()) >= threshold else "stable"
    batch.drift_json = {
        "metric": "risk_level_distribution",
        "previous_batch_id": previous.id,
        "threshold": threshold,
        "absolute_delta": deltas,
    }
