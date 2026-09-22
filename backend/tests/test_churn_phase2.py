import pandas as pd
import pytest

from app.churn.artifacts import save_training_artifacts
from app.churn.contracts import (
    CATEGORICAL_FEATURE_COLUMNS,
    EXPECTED_COLUMNS,
    EXPECTED_SCORING_COLUMNS,
    IDENTIFIER_COLUMN,
    TARGET_COLUMN,
)
from app.churn.dataset import load_churn_csv, load_churn_scoring_csv
from app.churn.inference import load_churn_model, score_students
from app.churn.training import train_logistic_baseline
from app.dao.churn_risk_dao import ChurnRiskDAO
from app.db.session import SessionLocal
from app.services.churn_risk_service import score_churn_csv_batch


def _sample_rows(count: int = 120) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for index in range(count):
        churned = index % 4 == 0
        row: dict[str, object] = {
            IDENTIFIER_COLUMN: f"score-student-{index}",
            "is_graduating": 1 if index % 3 == 0 else 0,
            "months_enrolled": 1 + index % 60,
            "monthly_fee": 180 + index % 12 * 25,
            "total_spend": "" if index == 0 else 300 + index * 40,
            TARGET_COLUMN: "Yes" if churned else "No",
        }
        for feature_index, column in enumerate(CATEGORICAL_FEATURE_COLUMNS):
            row[column] = "Yes" if (index + feature_index) % 2 == 0 else "No"
        rows.append(row)
    return rows


def _prepare_model_and_scoring_csv(tmp_path):
    training_path = tmp_path / "training.csv"
    source = pd.DataFrame(_sample_rows()).loc[:, EXPECTED_COLUMNS]
    source.to_csv(training_path, index=False)
    training_frame, quality = load_churn_csv(training_path)
    training_result = train_logistic_baseline(training_frame, target_recall=0.7)
    artifacts = save_training_artifacts(training_result, quality, tmp_path / "artifacts")

    scoring_path = tmp_path / "scoring.csv"
    source.loc[:, EXPECTED_SCORING_COLUMNS].to_csv(scoring_path, index=False)
    return artifacts.model_path, scoring_path


def test_scoring_csv_does_not_require_target_column(tmp_path):
    _, scoring_path = _prepare_model_and_scoring_csv(tmp_path)

    frame, quality = load_churn_scoring_csv(scoring_path)

    assert TARGET_COLUMN not in frame.columns
    assert quality.row_count == 120
    assert quality.missing_counts == {"total_spend": 1}


def test_score_students_rejects_invalid_medium_threshold(tmp_path):
    model_path, scoring_path = _prepare_model_and_scoring_csv(tmp_path)
    frame, _ = load_churn_scoring_csv(scoring_path)
    model = load_churn_model(model_path)

    with pytest.raises(ValueError, match="中风险阈值"):
        score_students(frame, model, medium_threshold=model.decision_threshold)


def test_batch_scoring_persists_traceable_results(tmp_path):
    model_path, scoring_path = _prepare_model_and_scoring_csv(tmp_path)

    with SessionLocal() as db:
        summary = score_churn_csv_batch(
            db,
            csv_path=scoring_path,
            model_path=model_path,
        )
        batch = ChurnRiskDAO().get_batch(db, summary.batch_id)
        predictions, prediction_total = ChurnRiskDAO().list_predictions(
            db,
            summary.batch_id,
            page_size=200,
        )

    assert batch is not None
    assert batch.status == "completed"
    assert batch.source_filename == "scoring.csv"
    assert len(batch.source_sha256) == 64
    assert summary.scored_count == 120
    assert summary.high_count + summary.medium_count + summary.low_count == 120
    assert len(predictions) == 120
    assert prediction_total == 120
    assert [item.risk_rank for item in predictions] == list(range(1, 121))
    assert len({item.student_external_id for item in predictions}) == 120
    assert predictions[0].risk_probability >= predictions[-1].risk_probability
