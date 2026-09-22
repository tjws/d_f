"""客户流失模型与评测报告的本地持久化。"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib

from app.churn.contracts import (
    FEATURE_COLUMNS,
    SCHEMA_VERSION,
    DataQualityReport,
    TemporalDataQualityReport,
)
from app.churn.training import TrainingResult


@dataclass(frozen=True)
class SavedArtifacts:
    model_path: Path
    report_path: Path


def save_training_artifacts(
    result: TrainingResult,
    quality: DataQualityReport | TemporalDataQualityReport,
    output_dir: str | Path,
) -> SavedArtifacts:
    """保存带数据契约的模型包和可直接阅读的 JSON 报告。"""

    directory = Path(output_dir).expanduser().resolve()
    directory.mkdir(parents=True, exist_ok=True)
    model_path = directory / "churn_logistic_baseline.joblib"
    report_path = directory / "churn_logistic_baseline_report.json"

    model_bundle: dict[str, Any] = {
        "model_name": result.report["model_name"],
        "schema_version": SCHEMA_VERSION,
        "trained_at": result.report["trained_at"],
        "feature_columns": list(FEATURE_COLUMNS),
        "threshold": result.threshold,
        "pipeline": result.pipeline,
    }
    joblib.dump(model_bundle, model_path)

    report = {
        **result.report,
        "data_quality": quality.to_dict(),
        "model_artifact": model_path.name,
    }
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return SavedArtifacts(model_path=model_path, report_path=report_path)
