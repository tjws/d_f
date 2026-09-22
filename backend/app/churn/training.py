"""客户流失基线模型训练编排。"""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

from app.churn.contracts import (
    FEATURE_COLUMNS,
    LABEL_WINDOW_END_COLUMN,
    OBSERVED_AT_COLUMN,
    SCHEMA_VERSION,
    TARGET_COLUMN,
)
from app.churn.evaluation import choose_threshold_for_recall, evaluate_probabilities
from app.churn.pipeline import build_logistic_pipeline


@dataclass(frozen=True)
class TrainingResult:
    pipeline: Pipeline
    threshold: float
    report: dict[str, Any]


def train_logistic_baseline(
    frame: pd.DataFrame,
    *,
    target_recall: float = 0.8,
    random_state: int = 42,
) -> TrainingResult:
    """使用训练/验证/测试三份互斥数据训练并评测基线模型。

    验证集只负责选择告警阈值，测试集只负责最终评测，避免用测试答案
    反过来调模型造成评测结果虚高。
    """

    features = frame.loc[:, FEATURE_COLUMNS]
    target = frame[TARGET_COLUMN].astype(int)
    if target.nunique() != 2:
        raise ValueError("训练数据必须同时包含流失和未流失样本")

    train_validation_x, test_x, train_validation_y, test_y = train_test_split(
        features,
        target,
        test_size=0.2,
        stratify=target,
        random_state=random_state,
    )
    train_x, validation_x, train_y, validation_y = train_test_split(
        train_validation_x,
        train_validation_y,
        test_size=0.25,
        stratify=train_validation_y,
        random_state=random_state,
    )

    pipeline = build_logistic_pipeline(random_state=random_state)
    pipeline.fit(train_x, train_y)

    validation_probabilities = pipeline.predict_proba(validation_x)[:, 1]
    threshold = choose_threshold_for_recall(
        validation_y.to_numpy(),
        validation_probabilities,
        target_recall=target_recall,
    )
    test_probabilities = pipeline.predict_proba(test_x)[:, 1]

    report = {
        "model_name": "logistic_regression_baseline",
        "schema_version": SCHEMA_VERSION,
        "trained_at": datetime.now(UTC).isoformat(),
        "random_state": random_state,
        "target_recall": target_recall,
        "split": {
            "train_rows": len(train_x),
            "validation_rows": len(validation_x),
            "test_rows": len(test_x),
        },
        "validation": evaluate_probabilities(
            validation_y.to_numpy(),
            validation_probabilities,
            threshold=threshold,
        ),
        "test": evaluate_probabilities(
            test_y.to_numpy(),
            test_probabilities,
            threshold=threshold,
        ),
        "feature_columns": list(FEATURE_COLUMNS),
        "identifier_excluded": True,
        "target_excluded": True,
        "notes": [
            "当前数据是静态快照，本报告只能验证离线分类能力，不能证明提前 30 天预警能力。",
            "阈值由验证集选择；测试集仅用于最终评测。",
            "模型输出只作为人工跟进排序依据，不自动联系客户。",
        ],
    }
    return TrainingResult(pipeline=pipeline, threshold=float(threshold), report=report)


def train_temporal_logistic_baseline(
    frame: pd.DataFrame,
    *,
    target_recall: float = 0.8,
    random_state: int = 42,
) -> TrainingResult:
    """按时间顺序训练，并清除标签窗口跨越下一分区的样本。"""

    ordered = frame.sort_values(OBSERVED_AT_COLUMN).reset_index(drop=True)
    if len(ordered) < 30:
        raise ValueError("时间型训练至少需要 30 条样本")
    validation_index = max(1, int(len(ordered) * 0.6))
    test_index = max(validation_index + 1, int(len(ordered) * 0.8))
    validation_start = ordered.iloc[validation_index][OBSERVED_AT_COLUMN]
    test_start = ordered.iloc[test_index][OBSERVED_AT_COLUMN]

    train = ordered[
        (ordered[OBSERVED_AT_COLUMN] < validation_start)
        & (ordered[LABEL_WINDOW_END_COLUMN] < validation_start)
    ]
    validation = ordered[
        (ordered[OBSERVED_AT_COLUMN] >= validation_start)
        & (ordered[OBSERVED_AT_COLUMN] < test_start)
        & (ordered[LABEL_WINDOW_END_COLUMN] < test_start)
    ]
    test = ordered[ordered[OBSERVED_AT_COLUMN] >= test_start]
    for name, part in (("训练集", train), ("验证集", validation), ("测试集", test)):
        if part.empty or part[TARGET_COLUMN].nunique() != 2:
            raise ValueError(f"{name}必须同时包含流失和未流失样本")

    pipeline = build_logistic_pipeline(random_state=random_state)
    pipeline.fit(train.loc[:, FEATURE_COLUMNS], train[TARGET_COLUMN].astype(int))
    validation_probabilities = pipeline.predict_proba(
        validation.loc[:, FEATURE_COLUMNS]
    )[:, 1]
    threshold = choose_threshold_for_recall(
        validation[TARGET_COLUMN].to_numpy(),
        validation_probabilities,
        target_recall=target_recall,
    )
    test_probabilities = pipeline.predict_proba(test.loc[:, FEATURE_COLUMNS])[:, 1]
    report = {
        "model_name": "logistic_regression_temporal_baseline",
        "schema_version": SCHEMA_VERSION,
        "trained_at": datetime.now(UTC).isoformat(),
        "random_state": random_state,
        "target_recall": target_recall,
        "split_strategy": "purged_time_split",
        "split": {
            "train_rows": len(train),
            "validation_rows": len(validation),
            "test_rows": len(test),
            "purged_rows": len(ordered) - len(train) - len(validation) - len(test),
            "validation_start": validation_start.isoformat(),
            "test_start": test_start.isoformat(),
        },
        "validation": evaluate_probabilities(
            validation[TARGET_COLUMN].to_numpy(),
            validation_probabilities,
            threshold=threshold,
        ),
        "test": evaluate_probabilities(
            test[TARGET_COLUMN].to_numpy(), test_probabilities, threshold=threshold
        ),
        "feature_columns": list(FEATURE_COLUMNS),
        "identifier_excluded": True,
        "target_excluded": True,
        "notes": [
            "按 observed_at 顺序切分，标签窗口跨越下一分区的样本已清除。",
            "模型只用于人工跟进排序，不自动联系客户。",
        ],
    }
    return TrainingResult(pipeline=pipeline, threshold=float(threshold), report=report)
