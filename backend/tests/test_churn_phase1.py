import json

import joblib
import pandas as pd
import pytest

from app.churn.artifacts import save_training_artifacts
from app.churn.contracts import (
    CATEGORICAL_FEATURE_COLUMNS,
    EXPECTED_COLUMNS,
    FEATURE_COLUMNS,
    IDENTIFIER_COLUMN,
    TARGET_COLUMN,
    ChurnDataError,
)
from app.churn.dataset import load_churn_csv
from app.churn.training import train_logistic_baseline


def _sample_rows(count: int = 80) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for index in range(count):
        churned = index % 4 == 0
        row: dict[str, object] = {
            IDENTIFIER_COLUMN: f"student-{index}",
            "is_graduating": 1 if index % 3 == 0 else 0,
            "months_enrolled": 2 + index % 48,
            "monthly_fee": 199 + index % 10 * 20,
            "total_spend": "" if index == 0 else 500 + index * 30,
            TARGET_COLUMN: "Yes" if churned else "No",
        }
        for feature_index, column in enumerate(CATEGORICAL_FEATURE_COLUMNS):
            row[column] = "Yes" if (index + feature_index) % 2 == 0 else "No"
        rows.append(row)
    return rows


def _write_csv(tmp_path, rows: list[dict[str, object]]):
    path = tmp_path / "churn.csv"
    pd.DataFrame(rows).loc[:, EXPECTED_COLUMNS].to_csv(path, index=False)
    return path


def test_load_churn_csv_cleans_data_and_builds_quality_report(tmp_path):
    csv_path = _write_csv(tmp_path, _sample_rows())

    frame, quality = load_churn_csv(csv_path)

    assert frame.loc[0, "total_spend"] != frame.loc[0, "total_spend"]  # NaN
    assert set(frame[TARGET_COLUMN]) == {0, 1}
    assert quality.row_count == 80
    assert quality.churned_count == 20
    assert quality.missing_counts == {"total_spend": 1}
    assert len(quality.source_sha256) == 64


def test_load_churn_csv_rejects_duplicate_student_id(tmp_path):
    rows = _sample_rows()
    rows[1][IDENTIFIER_COLUMN] = rows[0][IDENTIFIER_COLUMN]
    csv_path = _write_csv(tmp_path, rows)

    with pytest.raises(ChurnDataError, match="重复"):
        load_churn_csv(csv_path)


def test_train_and_save_baseline_artifacts(tmp_path):
    csv_path = _write_csv(tmp_path, _sample_rows(120))
    frame, quality = load_churn_csv(csv_path)

    result = train_logistic_baseline(frame, target_recall=0.7)
    saved = save_training_artifacts(result, quality, tmp_path / "artifacts")

    assert result.report["split"] == {
        "train_rows": 72,
        "validation_rows": 24,
        "test_rows": 24,
    }
    assert result.report["identifier_excluded"] is True
    assert IDENTIFIER_COLUMN not in result.report["feature_columns"]
    assert TARGET_COLUMN not in result.report["feature_columns"]
    assert 0 <= result.report["test"]["recall"] <= 1

    bundle = joblib.load(saved.model_path)
    assert bundle["feature_columns"] == FEATURE_COLUMNS
    assert bundle["pipeline"].predict_proba(frame.loc[:1, FEATURE_COLUMNS]).shape == (2, 2)

    report = json.loads(saved.report_path.read_text(encoding="utf-8"))
    assert report["data_quality"]["row_count"] == 120
    assert report["model_artifact"] == saved.model_path.name
