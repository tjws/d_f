"""客户流失 CSV 的读取、校验与清洗。"""

from hashlib import sha256
from pathlib import Path

import numpy as np
import pandas as pd

from app.churn.contracts import (
    CATEGORICAL_FEATURE_COLUMNS,
    EXPECTED_COLUMNS,
    EXPECTED_SCORING_COLUMNS,
    EXPECTED_TEMPORAL_COLUMNS,
    IDENTIFIER_COLUMN,
    LABEL_WINDOW_END_COLUMN,
    NUMERIC_FEATURE_COLUMNS,
    OBSERVED_AT_COLUMN,
    TARGET_COLUMN,
    ChurnDataError,
    DataQualityReport,
    ScoringDataQualityReport,
    TemporalDataQualityReport,
)


def _file_sha256(path: Path) -> str:
    """记录原始数据指纹，便于以后追溯模型由哪一版数据训练。"""

    digest = sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_and_validate_columns(
    path: Path,
    *,
    required_columns: list[str],
    optional_columns: set[str] | None = None,
) -> pd.DataFrame:
    frame = pd.read_csv(path, dtype=str, keep_default_na=False)
    frame.columns = [str(column).strip() for column in frame.columns]
    optional = optional_columns or set()
    missing_columns = sorted(set(required_columns) - set(frame.columns))
    unexpected_columns = sorted(set(frame.columns) - set(required_columns) - optional)
    if missing_columns or unexpected_columns:
        raise ChurnDataError(
            "CSV 字段不符合契约："
            f"缺少字段={missing_columns or '无'}，额外字段={unexpected_columns or '无'}"
        )
    return frame


def _clean_feature_frame(
    frame: pd.DataFrame, *, require_unique_student: bool = True
) -> tuple[pd.DataFrame, int, dict[str, int]]:
    """复用训练和评分所需的特征清洗规则。"""

    for column in frame.columns:
        frame[column] = frame[column].map(lambda value: value.strip() if isinstance(value, str) else value)
    if frame.empty:
        raise ChurnDataError("CSV 没有可处理的数据")
    if frame[IDENTIFIER_COLUMN].eq("").any():
        raise ChurnDataError("student_id 不能为空")

    duplicate_count = int(frame[IDENTIFIER_COLUMN].duplicated().sum())
    if require_unique_student and duplicate_count:
        raise ChurnDataError(f"student_id 存在 {duplicate_count} 条重复记录")

    for column in NUMERIC_FEATURE_COLUMNS:
        frame[column] = pd.to_numeric(frame[column].replace("", np.nan), errors="coerce")
    invalid_numeric = {
        column: int(frame[column].isna().sum())
        for column in NUMERIC_FEATURE_COLUMNS
        if column != "total_spend" and frame[column].isna().any()
    }
    if invalid_numeric:
        raise ChurnDataError(f"数值字段存在空值或非法内容：{invalid_numeric}")
    if not frame["is_graduating"].isin([0, 1]).all():
        raise ChurnDataError("is_graduating 只能是 0 或 1")
    for column in ("months_enrolled", "monthly_fee", "total_spend"):
        if frame[column].dropna().lt(0).any():
            raise ChurnDataError(f"{column} 不能为负数")

    for column in CATEGORICAL_FEATURE_COLUMNS:
        frame[column] = frame[column].replace("", np.nan)
    missing_counts = {
        column: int(count)
        for column, count in frame.isna().sum().items()
        if int(count) > 0
    }
    return frame, duplicate_count, missing_counts


def load_temporal_churn_csv(
    csv_path: str | Path,
    *,
    label_horizon_days: int = 30,
) -> tuple[pd.DataFrame, TemporalDataQualityReport]:
    """读取真正可做提前预警验证的时间快照数据。

    同一学生可以有多期快照，但同一观察日只能有一条；标签窗口必须严格位于
    观察日之后，训练阶段还会清除跨越数据切分边界的样本以防未来信息泄漏。
    """

    if label_horizon_days <= 0:
        raise ChurnDataError("标签窗口天数必须大于 0")
    path = Path(csv_path).expanduser().resolve()
    if not path.is_file():
        raise ChurnDataError(f"找不到客户流失时间型 CSV：{path}")
    frame = _read_and_validate_columns(path, required_columns=EXPECTED_TEMPORAL_COLUMNS)
    frame = frame.loc[:, EXPECTED_TEMPORAL_COLUMNS].copy()
    for column in frame.columns:
        frame[column] = frame[column].map(
            lambda value: value.strip() if isinstance(value, str) else value
        )
    unknown_targets = sorted(set(frame[TARGET_COLUMN]) - {"Yes", "No"})
    if unknown_targets:
        raise ChurnDataError(f"is_churned 只能是 Yes/No，发现：{unknown_targets}")
    frame[TARGET_COLUMN] = frame[TARGET_COLUMN].map({"No": 0, "Yes": 1}).astype("int8")
    for column in (OBSERVED_AT_COLUMN, LABEL_WINDOW_END_COLUMN):
        frame[column] = pd.to_datetime(frame[column], utc=True, errors="coerce")
        if frame[column].isna().any():
            raise ChurnDataError(f"{column} 存在空值或非法日期")
    duplicate_snapshots = int(
        frame.duplicated([IDENTIFIER_COLUMN, OBSERVED_AT_COLUMN]).sum()
    )
    if duplicate_snapshots:
        raise ChurnDataError(f"学生观察快照存在 {duplicate_snapshots} 条重复记录")
    horizons = (
        frame[LABEL_WINDOW_END_COLUMN] - frame[OBSERVED_AT_COLUMN]
    ).dt.total_seconds() / 86400
    if not (horizons == label_horizon_days).all():
        raise ChurnDataError(
            f"label_window_end 必须等于 observed_at 后 {label_horizon_days} 天"
        )
    frame, _, missing_counts = _clean_feature_frame(
        frame, require_unique_student=False
    )
    churned_count = int(frame[TARGET_COLUMN].sum())
    quality = TemporalDataQualityReport(
        source_path=str(path),
        source_sha256=_file_sha256(path),
        row_count=len(frame),
        churned_count=churned_count,
        churn_rate=round(churned_count / len(frame), 6),
        snapshot_count=int(frame[OBSERVED_AT_COLUMN].nunique()),
        observed_from=frame[OBSERVED_AT_COLUMN].min().isoformat(),
        observed_to=frame[OBSERVED_AT_COLUMN].max().isoformat(),
        label_horizon_days=label_horizon_days,
        duplicate_snapshots=duplicate_snapshots,
        missing_counts=missing_counts,
    )
    return frame, quality


def load_churn_csv(csv_path: str | Path) -> tuple[pd.DataFrame, DataQualityReport]:
    """读取并清洗流失样本，同时返回可审计的数据质量摘要。

    这里采用严格列契约：多列可能把未来信息误当特征，少列则会让训练结果失真，
    因此两种情况都直接失败，而不是静默忽略。
    """

    path = Path(csv_path).expanduser().resolve()
    if not path.is_file():
        raise ChurnDataError(f"找不到客户流失 CSV：{path}")

    frame = _read_and_validate_columns(path, required_columns=EXPECTED_COLUMNS)

    # 固定列顺序，保证同一份数据在不同机器上的处理流程一致。
    frame = frame.loc[:, EXPECTED_COLUMNS].copy()
    for column in frame.columns:
        frame[column] = frame[column].map(lambda value: value.strip() if isinstance(value, str) else value)

    unknown_targets = sorted(set(frame[TARGET_COLUMN]) - {"Yes", "No"})
    if unknown_targets:
        raise ChurnDataError(f"is_churned 只能是 Yes/No，发现：{unknown_targets}")
    frame[TARGET_COLUMN] = frame[TARGET_COLUMN].map({"No": 0, "Yes": 1}).astype("int8")

    frame, duplicate_count, missing_counts = _clean_feature_frame(frame)
    churned_count = int(frame[TARGET_COLUMN].sum())
    quality = DataQualityReport(
        source_path=str(path),
        source_sha256=_file_sha256(path),
        row_count=len(frame),
        churned_count=churned_count,
        churn_rate=round(churned_count / len(frame), 6),
        duplicate_student_ids=duplicate_count,
        missing_counts=missing_counts,
    )
    return frame, quality


def load_churn_scoring_csv(
    csv_path: str | Path,
) -> tuple[pd.DataFrame, ScoringDataQualityReport]:
    """读取待评分数据；允许带上历史标签，但评分逻辑会明确丢弃该答案列。"""

    path = Path(csv_path).expanduser().resolve()
    if not path.is_file():
        raise ChurnDataError(f"找不到客户流失评分 CSV：{path}")

    frame = _read_and_validate_columns(
        path,
        required_columns=EXPECTED_SCORING_COLUMNS,
        optional_columns={TARGET_COLUMN},
    )
    frame = frame.loc[:, EXPECTED_SCORING_COLUMNS].copy()
    frame, duplicate_count, missing_counts = _clean_feature_frame(frame)
    quality = ScoringDataQualityReport(
        source_path=str(path),
        source_filename=path.name,
        source_sha256=_file_sha256(path),
        row_count=len(frame),
        duplicate_student_ids=duplicate_count,
        missing_counts=missing_counts,
    )
    return frame, quality
