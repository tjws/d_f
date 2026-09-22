"""客户流失模型的阈值选择与业务评测。"""

from math import ceil

import numpy as np
from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
)


def choose_threshold_for_recall(
    y_true: np.ndarray,
    probabilities: np.ndarray,
    *,
    target_recall: float,
) -> float:
    """在验证集上选择满足目标召回率且精确率尽量高的阈值。"""

    if not 0 < target_recall <= 1:
        raise ValueError("target_recall 必须位于 (0, 1] 区间")

    precision, recall, thresholds = precision_recall_curve(y_true, probabilities)
    candidates = np.flatnonzero(recall[:-1] >= target_recall)
    if not len(candidates):
        return 0.0

    candidate_precision = precision[:-1][candidates]
    best_precision = candidate_precision.max()
    best_candidates = candidates[candidate_precision == best_precision]
    # 精确率相同时选择更高阈值，减少不必要的销售跟进量。
    return float(thresholds[best_candidates].max())


def evaluate_probabilities(
    y_true: np.ndarray,
    probabilities: np.ndarray,
    *,
    threshold: float,
    top_fraction: float = 0.2,
) -> dict[str, object]:
    """同时输出模型指标和销售可理解的 Top-K 命中指标。"""

    if not 0 < top_fraction <= 1:
        raise ValueError("top_fraction 必须位于 (0, 1] 区间")

    labels = (probabilities >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, labels, labels=[0, 1]).ravel()

    top_count = max(1, ceil(len(probabilities) * top_fraction))
    top_indices = np.argsort(probabilities)[::-1][:top_count]
    top_positives = int(np.asarray(y_true)[top_indices].sum())
    all_positives = int(np.asarray(y_true).sum())
    base_rate = float(np.asarray(y_true).mean())
    precision_at_top = top_positives / top_count

    return {
        "threshold": round(float(threshold), 6),
        "precision": round(float(precision_score(y_true, labels, zero_division=0)), 6),
        "recall": round(float(recall_score(y_true, labels, zero_division=0)), 6),
        "f1": round(float(f1_score(y_true, labels, zero_division=0)), 6),
        "pr_auc": round(float(average_precision_score(y_true, probabilities)), 6),
        "roc_auc": round(float(roc_auc_score(y_true, probabilities)), 6),
        "confusion_matrix": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
        "top_fraction": top_fraction,
        "top_count": top_count,
        "precision_at_top": round(precision_at_top, 6),
        "recall_at_top": round(top_positives / all_positives if all_positives else 0.0, 6),
        "lift_at_top": round(precision_at_top / base_rate if base_rate else 0.0, 6),
    }

