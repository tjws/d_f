"""客户流失模型加载与纯计算评分逻辑。"""

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

from app.churn.contracts import FEATURE_COLUMNS, IDENTIFIER_COLUMN, SCHEMA_VERSION, ChurnDataError


@dataclass(frozen=True)
class LoadedChurnModel:
    model_name: str
    schema_version: str
    trained_at: str | None
    artifact_sha256: str
    decision_threshold: float
    pipeline: Any


@dataclass(frozen=True)
class ScoredStudent:
    student_external_id: str
    risk_probability: float
    risk_level: str
    predicted_churn: bool
    risk_rank: int
    risk_percentile: float


def _file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_churn_model(model_path: str | Path) -> LoadedChurnModel:
    """加载本系统生成的可信模型包，并核对数据契约。

    joblib 可以执行 Python 序列化对象，调用方不得传入下载或来源不明的文件。
    """

    path = Path(model_path).expanduser().resolve()
    if not path.is_file():
        raise ChurnDataError(f"找不到客户流失模型：{path}")

    bundle = joblib.load(path)
    if not isinstance(bundle, dict):
        raise ChurnDataError("客户流失模型包格式无效")
    if bundle.get("schema_version") != SCHEMA_VERSION:
        raise ChurnDataError("客户流失模型的数据契约版本不兼容")
    if bundle.get("feature_columns") != FEATURE_COLUMNS:
        raise ChurnDataError("客户流失模型的特征字段与当前代码不一致")

    pipeline = bundle.get("pipeline")
    if pipeline is None or not callable(getattr(pipeline, "predict_proba", None)):
        raise ChurnDataError("客户流失模型缺少概率预测能力")
    threshold = float(bundle.get("threshold", -1))
    if not 0 <= threshold <= 1:
        raise ChurnDataError("客户流失模型的决策阈值无效")

    return LoadedChurnModel(
        model_name=str(bundle.get("model_name", "logistic_regression_baseline")),
        schema_version=str(bundle["schema_version"]),
        trained_at=str(bundle["trained_at"]) if bundle.get("trained_at") else None,
        artifact_sha256=_file_sha256(path),
        decision_threshold=threshold,
        pipeline=pipeline,
    )


def resolve_medium_threshold(
    model: LoadedChurnModel,
    medium_threshold: float | None,
) -> float:
    """解析并校验业务中风险阈值。"""

    resolved_medium = (
        float(medium_threshold)
        if medium_threshold is not None
        else round(model.decision_threshold * 0.6, 6)
    )
    if not 0 <= resolved_medium < model.decision_threshold:
        raise ValueError("中风险阈值必须大于等于 0，且小于模型高风险阈值")
    return resolved_medium


def score_students(
    frame: pd.DataFrame,
    model: LoadedChurnModel,
    *,
    medium_threshold: float | None = None,
) -> tuple[list[ScoredStudent], float]:
    """按概率从高到低排名，并把模型阈值转换成业务可读风险等级。"""

    resolved_medium = resolve_medium_threshold(model, medium_threshold)

    probabilities = np.asarray(model.pipeline.predict_proba(frame.loc[:, FEATURE_COLUMNS])[:, 1])
    order = np.argsort(-probabilities, kind="stable")
    ranks = np.empty(len(frame), dtype=int)
    ranks[order] = np.arange(1, len(frame) + 1)

    results: list[ScoredStudent] = []
    for row_index, probability in enumerate(probabilities):
        rank = int(ranks[row_index])
        probability_value = float(probability)
        if probability_value >= model.decision_threshold:
            level = "high"
        elif probability_value >= resolved_medium:
            level = "medium"
        else:
            level = "low"
        results.append(
            ScoredStudent(
                student_external_id=str(frame.iloc[row_index][IDENTIFIER_COLUMN]),
                risk_probability=probability_value,
                risk_level=level,
                predicted_churn=probability_value >= model.decision_threshold,
                risk_rank=rank,
                risk_percentile=round((len(frame) - rank + 1) / len(frame), 6),
            )
        )
    return results, resolved_medium
