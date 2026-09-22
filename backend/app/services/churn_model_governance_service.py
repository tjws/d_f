"""流失模型登记、审批与受控评分入口。"""

from datetime import datetime, timezone
import json
import os
from pathlib import Path

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.churn.inference import load_churn_model, resolve_medium_threshold
from app.dao.churn_model_version_dao import ChurnModelVersionDAO
from app.db.session import SessionLocal
from app.models.churn_model_version import ChurnModelVersion
from app.models.user import User
from app.schemas.churn_risk import ChurnModelRegister, ChurnScoringRequest
from app.services.audit_log_service import append_audit_log
from app.services.churn_risk_service import score_churn_csv_batch


model_dao = ChurnModelVersionDAO()


def _backend_dir() -> Path:
    return Path(__file__).resolve().parents[2]


def churn_model_directory() -> Path:
    return Path(
        os.getenv("CHURN_MODEL_DIRECTORY", str(_backend_dir() / "data" / "churn_artifacts"))
    ).expanduser().resolve()


def churn_import_directory() -> Path:
    return Path(
        os.getenv("CHURN_IMPORT_DIRECTORY", str(_backend_dir() / "data" / "churn_imports"))
    ).expanduser().resolve()


def _safe_child(root: Path, filename: str, *, must_exist: bool = True) -> Path:
    if Path(filename).name != filename:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="只能使用配置目录中的文件名，不能包含路径",
        )
    path = (root / filename).resolve()
    if not path.is_relative_to(root):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="文件路径无效")
    if must_exist and not path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文件不存在")
    return path


def register_churn_model(
    db: Session, current_user: User, payload: ChurnModelRegister
) -> dict[str, object]:
    artifact_path = _safe_child(churn_model_directory(), payload.artifact_filename)
    loaded = load_churn_model(artifact_path)
    normalized_version = payload.version.strip()
    version_match = model_dao.get_by_version(db, normalized_version)
    if version_match is not None and version_match.artifact_sha256 != loaded.artifact_sha256:
        raise HTTPException(status_code=409, detail="该模型版本号已用于其他模型产物")
    existing = model_dao.get_by_sha256(db, loaded.artifact_sha256)
    if existing is not None:
        return model_version_read(existing)

    metrics: dict = {}
    if payload.report_filename:
        report_path = _safe_child(churn_model_directory(), payload.report_filename)
        try:
            report = json.loads(report_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="模型评测报告不是有效 JSON",
            ) from exc
        if report.get("model_name") != loaded.model_name:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="评测报告与模型名称不一致",
            )
        metrics = report.get("test") if isinstance(report.get("test"), dict) else {}

    try:
        medium_threshold = resolve_medium_threshold(loaded, payload.medium_threshold)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    model = ChurnModelVersion(
        version=normalized_version,
        model_name=loaded.model_name,
        schema_version=loaded.schema_version,
        artifact_filename=payload.artifact_filename,
        artifact_sha256=loaded.artifact_sha256,
        status="candidate",
        decision_threshold=loaded.decision_threshold,
        medium_threshold=medium_threshold,
        metrics_json=metrics,
    )
    model_dao.add(db, model)
    db.flush()
    append_audit_log(
        db,
        current_user,
        "churn.model_registered",
        "churn_model_version",
        str(model.id),
        {"version": model.version, "status": model.status},
    )
    db.commit()
    db.refresh(model)
    return model_version_read(model)


def approve_churn_model(
    db: Session, current_user: User, model_id: int
) -> dict[str, object]:
    model = model_dao.get_by_id(db, model_id)
    if model is None:
        raise HTTPException(status_code=404, detail="流失模型版本不存在")
    if model.status == "approved":
        return model_version_read(model)
    now = datetime.now(timezone.utc)
    for approved in model_dao.list_approved(db):
        approved.status = "retired"
    model.status = "approved"
    model.approved_by = current_user.id
    model.approved_at = now
    append_audit_log(
        db,
        current_user,
        "churn.model_approved",
        "churn_model_version",
        str(model.id),
        {"version": model.version},
    )
    db.commit()
    db.refresh(model)
    return model_version_read(model)


def list_churn_models(db: Session) -> list[dict[str, object]]:
    return [model_version_read(model) for model in model_dao.list_all(db)]


def request_churn_scoring(
    db: Session, current_user: User, payload: ChurnScoringRequest
) -> dict[str, object]:
    model = (
        model_dao.get_by_id(db, payload.model_version_id)
        if payload.model_version_id is not None
        else model_dao.get_approved(db)
    )
    if model is None or model.status != "approved":
        raise HTTPException(status_code=409, detail="请先审批一个流失模型版本")
    source_path = _safe_child(churn_import_directory(), payload.source_filename)
    model_path = _safe_child(churn_model_directory(), model.artifact_filename)
    if payload.execution_mode == "sync":
        summary = score_churn_csv_batch(
            db,
            csv_path=source_path,
            model_path=model_path,
            medium_threshold=model.medium_threshold,
            source_system=payload.source_system,
            trigger_source="api",
            model_version_id=model.id,
            observation_at=payload.observation_at,
        )
        return {"status": "completed", "batch_id": summary.batch_id, "message_id": None}

    from app.workers.churn_tasks import execute_churn_scoring_task

    message = execute_churn_scoring_task.send(
        source_path.name,
        model.id,
        payload.source_system,
        payload.observation_at.isoformat() if payload.observation_at else None,
        "api",
    )
    append_audit_log(
        db,
        current_user,
        "churn.scoring_queued",
        "churn_model_version",
        str(model.id),
        {"source_filename": source_path.name, "source_system": payload.source_system},
    )
    db.commit()
    return {"status": "queued", "batch_id": None, "message_id": message.message_id}


def execute_registered_churn_scoring(
    source_filename: str,
    model_version_id: int,
    source_system: str,
    observation_at: str | None,
    trigger_source: str,
) -> int:
    """Worker 重新从数据库解析已审批模型，不能信任消息里传入任意路径。"""

    with SessionLocal() as db:
        model = model_dao.get_by_id(db, model_version_id)
        if model is None or model.status != "approved":
            raise ValueError("approved churn model is required")
        parsed_observation = datetime.fromisoformat(observation_at) if observation_at else None
        summary = score_churn_csv_batch(
            db,
            csv_path=_safe_child(churn_import_directory(), source_filename),
            model_path=_safe_child(churn_model_directory(), model.artifact_filename),
            medium_threshold=model.medium_threshold,
            source_system=source_system,
            trigger_source=trigger_source,
            model_version_id=model.id,
            observation_at=parsed_observation,
        )
        return summary.batch_id


def model_version_read(model: ChurnModelVersion) -> dict[str, object]:
    return {
        "id": model.id,
        "version": model.version,
        "model_name": model.model_name,
        "schema_version": model.schema_version,
        "artifact_filename": model.artifact_filename,
        "artifact_sha256": model.artifact_sha256,
        "status": model.status,
        "decision_threshold": model.decision_threshold,
        "medium_threshold": model.medium_threshold,
        "metrics": model.metrics_json,
        "approved_by": model.approved_by,
        "approved_at": model.approved_at,
        "created_at": model.created_at,
    }
