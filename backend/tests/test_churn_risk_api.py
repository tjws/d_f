import uuid
from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.session import SessionLocal
from app.main import app
from app.models.churn_risk_prediction import ChurnRiskPrediction
from app.models.churn_scoring_batch import ChurnScoringBatch
from app.models.user import User


client = TestClient(app)


def _user_headers(role: str) -> dict[str, str]:
    username = f"churn_api_{role}_{uuid.uuid4().hex[:8]}"
    password = "Test123!"
    assert client.post("/auth/register", json={"username": username, "password": password}).status_code == 201
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.username == username))
        assert user is not None
        user.role = role
        db.commit()
    login = client.post("/auth/token", data={"username": username, "password": password})
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _create_batch() -> int:
    now = datetime.now(timezone.utc)
    with SessionLocal() as db:
        batch = ChurnScoringBatch(
            status="completed",
            model_name="logistic_regression_baseline",
            model_schema_version="churn_features_v1",
            model_artifact_sha256="a" * 64,
            source_filename="risk-test.csv",
            source_sha256="b" * 64,
            decision_threshold=0.48,
            medium_threshold=0.29,
            row_count=3,
            scored_count=3,
            high_count=1,
            medium_count=1,
            low_count=1,
            finished_at=now,
        )
        db.add(batch)
        db.flush()
        db.add_all(
            [
                ChurnRiskPrediction(
                    batch_id=batch.id,
                    student_external_id="STUDENT-HIGH",
                    risk_probability=0.91,
                    risk_level="high",
                    predicted_churn=True,
                    risk_rank=1,
                    risk_percentile=1.0,
                ),
                ChurnRiskPrediction(
                    batch_id=batch.id,
                    student_external_id="STUDENT-MEDIUM",
                    risk_probability=0.36,
                    risk_level="medium",
                    predicted_churn=False,
                    risk_rank=2,
                    risk_percentile=0.666667,
                ),
                ChurnRiskPrediction(
                    batch_id=batch.id,
                    student_external_id="STUDENT-LOW",
                    risk_probability=0.12,
                    risk_level="low",
                    predicted_churn=False,
                    risk_rank=3,
                    risk_percentile=0.333333,
                ),
            ]
        )
        db.commit()
        return batch.id


def test_admin_and_manager_can_read_churn_batches_and_filtered_predictions():
    batch_id = _create_batch()
    admin_headers = _user_headers("admin")

    batches = client.get("/admin/churn-risks/batches?status=completed", headers=admin_headers)
    assert batches.status_code == 200
    assert any(item["id"] == batch_id for item in batches.json()["items"])

    detail = client.get(
        f"/admin/churn-risks/batches/{batch_id}?risk_level=high&keyword=HIGH&page=1&page_size=20",
        headers=admin_headers,
    )
    assert detail.status_code == 200
    payload = detail.json()
    assert payload["batch"]["id"] == batch_id
    assert payload["total"] == 1
    assert payload["items"][0]["student_external_id"] == "STUDENT-HIGH"
    assert payload["items"][0]["risk_score"] == 0.91
    assert "risk_probability" not in payload["items"][0]

    manager_headers = _user_headers("manager")
    assert client.get("/admin/churn-risks/batches", headers=manager_headers).status_code == 200


def test_sales_only_receive_scoped_churn_risks_and_missing_batch_returns_404():
    sales_headers = _user_headers("sales")
    scoped = client.get("/admin/churn-risks/batches", headers=sales_headers)
    assert scoped.status_code == 200
    assert scoped.json()["items"] == []

    admin_headers = _user_headers("admin")
    missing = client.get("/admin/churn-risks/batches/99999999", headers=admin_headers)
    assert missing.status_code == 404
