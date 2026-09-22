"""客户流失数据契约。

集中声明 CSV 字段和特征边界，避免训练脚本、测试和后续批量预测各自维护一套字段。
"""

from dataclasses import asdict, dataclass
from typing import Any


SCHEMA_VERSION = "churn_features_v1"
IDENTIFIER_COLUMN = "student_id"
TARGET_COLUMN = "is_churned"
OBSERVED_AT_COLUMN = "observed_at"
LABEL_WINDOW_END_COLUMN = "label_window_end"

NUMERIC_FEATURE_COLUMNS = [
    "is_graduating",
    "months_enrolled",
    "monthly_fee",
    "total_spend",
]

CATEGORICAL_FEATURE_COLUMNS = [
    "gender",
    "multi_child_family",
    "from_referral",
    "has_core_course",
    "core_course_count",
    "class_type",
    "svc_homework_tutoring",
    "svc_progress_report",
    "svc_contest_coaching",
    "svc_study_companion",
    "svc_parent_class",
    "svc_admission_planning",
    "purchase_cycle",
    "e_contract",
    "payment_method",
]

FEATURE_COLUMNS = NUMERIC_FEATURE_COLUMNS + CATEGORICAL_FEATURE_COLUMNS
EXPECTED_COLUMNS = [IDENTIFIER_COLUMN, *FEATURE_COLUMNS, TARGET_COLUMN]
EXPECTED_SCORING_COLUMNS = [IDENTIFIER_COLUMN, *FEATURE_COLUMNS]
EXPECTED_TEMPORAL_COLUMNS = [
    IDENTIFIER_COLUMN,
    OBSERVED_AT_COLUMN,
    LABEL_WINDOW_END_COLUMN,
    *FEATURE_COLUMNS,
    TARGET_COLUMN,
]


class ChurnDataError(ValueError):
    """输入数据不符合流失模型契约时抛出的业务异常。"""


@dataclass(frozen=True)
class DataQualityReport:
    """一次 CSV 导入的数据质量摘要。"""

    source_path: str
    source_sha256: str
    row_count: int
    churned_count: int
    churn_rate: float
    duplicate_student_ids: int
    missing_counts: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ScoringDataQualityReport:
    """一次待评分 CSV 的数据质量摘要，不要求包含已知流失答案。"""

    source_path: str
    source_filename: str
    source_sha256: str
    row_count: int
    duplicate_student_ids: int
    missing_counts: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TemporalDataQualityReport:
    """带观察日和未来标签窗口的时间型训练数据摘要。"""

    source_path: str
    source_sha256: str
    row_count: int
    churned_count: int
    churn_rate: float
    snapshot_count: int
    observed_from: str
    observed_to: str
    label_horizon_days: int
    duplicate_snapshots: int
    missing_counts: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
