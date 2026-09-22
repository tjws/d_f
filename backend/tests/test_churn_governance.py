import uuid

import pandas as pd
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.churn.artifacts import save_training_artifacts
from app.churn.contracts import (
    CATEGORICAL_FEATURE_COLUMNS,
    EXPECTED_COLUMNS,
    EXPECTED_SCORING_COLUMNS,
    IDENTIFIER_COLUMN,
    TARGET_COLUMN,
)
from app.churn.dataset import load_churn_csv
from app.churn.training import train_logistic_baseline
from app.db.session import SessionLocal
from app.main import app
from app.models.user import User


client = TestClient(app)


def _admin_headers() -> dict[str, str]:
    username = f"churn_governance_{uuid.uuid4().hex[:8]}"
    password = "Test123!"
    assert client.post("/auth/register", json={"username": username, "password": password}).status_code == 201
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.username == username))
        assert user is not None
        user.role = "admin"
        db.commit()
    token = client.post("/auth/token", data={"username": username, "password": password})
    return {"Authorization": f"Bearer {token.json()['access_token']}"}


def _rows(count: int = 120) -> list[dict[str, object]]:
    rows = []
    for index in range(count):
        row: dict[str, object] = {
            IDENTIFIER_COLUMN: f"governance-{index}",
            "is_graduating": index % 2,
            "months_enrolled": 1 + index % 40,
            "monthly_fee": 200 + index % 8 * 20,
            "total_spend": 400 + index * 30,
            TARGET_COLUMN: "Yes" if index % 4 == 0 else "No",
        }
        for feature_index, column in enumerate(CATEGORICAL_FEATURE_COLUMNS):
            row[column] = "Yes" if (index + feature_index) % 2 == 0 else "No"
        rows.append(row)
    return rows


def test_model_approval_and_scoring_idempotency(tmp_path, monkeypatch):
    model_dir = tmp_path / "models"
    import_dir = tmp_path / "imports"
    import_dir.mkdir()
    monkeypatch.setenv("CHURN_MODEL_DIRECTORY", str(model_dir))
    monkeypatch.setenv("CHURN_IMPORT_DIRECTORY", str(import_dir))

    source = pd.DataFrame(_rows()).loc[:, EXPECTED_COLUMNS]
    training_path = tmp_path / "training.csv"
    source.to_csv(training_path, index=False)
    frame, quality = load_churn_csv(training_path)
    result = train_logistic_baseline(frame, target_recall=0.7)
    saved = save_training_artifacts(result, quality, model_dir)
    scoring_name = "governance-score.csv"
    source.loc[:, EXPECTED_SCORING_COLUMNS].to_csv(import_dir / scoring_name, index=False)

    headers = _admin_headers()
    registered = client.post(
        "/admin/churn-risks/models",
        headers=headers,
        json={
            "version": f"test-{uuid.uuid4().hex[:8]}",
            "artifact_filename": saved.model_path.name,
            "report_filename": saved.report_path.name,
        },
    )
    assert registered.status_code == 201
    model = registered.json()
    assert model["status"] == "candidate"

    approved = client.post(
        f"/admin/churn-risks/models/{model['id']}/approve", headers=headers
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"

    payload = {
        "source_filename": scoring_name,
        "source_system": f"governance-{uuid.uuid4().hex[:6]}",
        "model_version_id": model["id"],
        "execution_mode": "sync",
    }
    first = client.post("/admin/churn-risks/score", headers=headers, json=payload)
    second = client.post("/admin/churn-risks/score", headers=headers, json=payload)
    assert first.status_code == 202
    assert second.status_code == 202
    assert first.json()["batch_id"] == second.json()["batch_id"]

    listed = client.get("/admin/churn-risks/models", headers=headers)
    assert listed.status_code == 200
    assert any(item["id"] == model["id"] for item in listed.json())
