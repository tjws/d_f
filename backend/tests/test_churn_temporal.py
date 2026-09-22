from datetime import datetime, timedelta, timezone

import pandas as pd
import pytest

from app.churn.contracts import (
    CATEGORICAL_FEATURE_COLUMNS,
    EXPECTED_TEMPORAL_COLUMNS,
    IDENTIFIER_COLUMN,
    LABEL_WINDOW_END_COLUMN,
    OBSERVED_AT_COLUMN,
    TARGET_COLUMN,
    ChurnDataError,
)
from app.churn.dataset import load_temporal_churn_csv
from app.churn.training import train_temporal_logistic_baseline


def _temporal_rows(count: int = 240) -> list[dict[str, object]]:
    start = datetime(2025, 1, 1, tzinfo=timezone.utc)
    rows = []
    for index in range(count):
        observed = start + timedelta(days=index)
        row: dict[str, object] = {
            IDENTIFIER_COLUMN: f"temporal-{index}",
            OBSERVED_AT_COLUMN: observed.isoformat(),
            LABEL_WINDOW_END_COLUMN: (observed + timedelta(days=30)).isoformat(),
            "is_graduating": index % 2,
            "months_enrolled": 1 + index % 50,
            "monthly_fee": 200 + index % 7 * 30,
            "total_spend": 500 + index * 20,
            TARGET_COLUMN: "Yes" if index % 4 == 0 else "No",
        }
        for feature_index, column in enumerate(CATEGORICAL_FEATURE_COLUMNS):
            row[column] = "Yes" if (index + feature_index) % 2 == 0 else "No"
        rows.append(row)
    return rows


def test_temporal_contract_and_purged_time_split(tmp_path):
    path = tmp_path / "temporal.csv"
    pd.DataFrame(_temporal_rows()).loc[:, EXPECTED_TEMPORAL_COLUMNS].to_csv(path, index=False)

    frame, quality = load_temporal_churn_csv(path, label_horizon_days=30)
    result = train_temporal_logistic_baseline(frame, target_recall=0.7)

    assert quality.label_horizon_days == 30
    assert quality.snapshot_count == 240
    assert result.report["split_strategy"] == "purged_time_split"
    assert result.report["split"]["purged_rows"] > 0
    assert result.report["split"]["train_rows"] > 0
    assert result.report["split"]["validation_rows"] > 0
    assert result.report["split"]["test_rows"] > 0


def test_temporal_contract_rejects_wrong_label_horizon(tmp_path):
    rows = _temporal_rows(40)
    rows[0][LABEL_WINDOW_END_COLUMN] = (
        datetime.fromisoformat(str(rows[0][OBSERVED_AT_COLUMN])) + timedelta(days=7)
    ).isoformat()
    path = tmp_path / "bad-temporal.csv"
    pd.DataFrame(rows).loc[:, EXPECTED_TEMPORAL_COLUMNS].to_csv(path, index=False)

    with pytest.raises(ChurnDataError, match="30 天"):
        load_temporal_churn_csv(path, label_horizon_days=30)
