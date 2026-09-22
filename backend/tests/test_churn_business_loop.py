import uuid
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.db.session import SessionLocal
from app.main import app
from app.models.churn_risk_prediction import ChurnRiskPrediction
from app.models.churn_risk_intervention import ChurnRiskIntervention
from app.models.churn_scoring_batch import ChurnScoringBatch
from app.models.external_student_mapping import ExternalStudentMapping
from app.models.schedule import Schedule
from app.models.timeline_event import TimelineEvent
from app.models.user import User


client = TestClient(app)


def _headers(role: str) -> dict[str, str]:
    username = f"churn_loop_{role}_{uuid.uuid4().hex[:8]}"
    password = "Test123!"
    assert client.post("/auth/register", json={"username": username, "password": password}).status_code == 201
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.username == username))
        assert user is not None
        user.role = role
        db.commit()
    token = client.post("/auth/token", data={"username": username, "password": password})
    assert token.status_code == 200
    return {"Authorization": f"Bearer {token.json()['access_token']}"}


def test_external_mapping_enables_scoped_human_intervention_loop():
    sales_headers = _headers("sales")
    admin_headers = _headers("admin")
    customer = client.post(
        "/customers",
        headers=sales_headers,
        json={"name": "流失跟进客户", "phone": "13800138066"},
    )
    assert customer.status_code == 201
    customer_id = customer.json()["id"]
    student = client.post(
        f"/customers/{customer_id}/students",
        headers=sales_headers,
        json={"name": "流失测试学生", "grade": "初二"},
    )
    assert student.status_code == 201
    student_id = student.json()["id"]

    with SessionLocal() as db:
        batch = ChurnScoringBatch(
            status="completed",
            model_name="loop-model",
            model_schema_version="churn_features_v1",
            model_artifact_sha256=uuid.uuid4().hex * 2,
            source_filename="loop.csv",
            source_sha256=uuid.uuid4().hex * 2,
            source_system="crm_demo",
            decision_threshold=0.5,
            medium_threshold=0.3,
            row_count=1,
            scored_count=1,
            high_count=1,
            medium_count=0,
            low_count=0,
            finished_at=datetime.now(timezone.utc),
        )
        db.add(batch)
        db.flush()
        prediction = ChurnRiskPrediction(
            batch_id=batch.id,
            student_external_id="CRM-STUDENT-001",
            risk_probability=0.88,
            risk_level="high",
            predicted_churn=True,
            risk_rank=1,
            risk_percentile=1.0,
        )
        db.add(prediction)
        db.commit()
        batch_id = batch.id
        prediction_id = prediction.id

    before = client.get(f"/admin/churn-risks/batches/{batch_id}", headers=sales_headers)
    assert before.status_code == 200
    assert before.json()["items"] == []

    mapping = client.post(
        "/admin/churn-risks/mappings",
        headers=admin_headers,
        json={
            "source_system": "crm_demo",
            "external_student_id": "CRM-STUDENT-001",
            "student_id": student_id,
        },
    )
    assert mapping.status_code == 201
    assert mapping.json()["rebound_prediction_count"] == 1

    visible = client.get(f"/admin/churn-risks/batches/{batch_id}", headers=sales_headers)
    assert visible.status_code == 200
    item = visible.json()["items"][0]
    assert item["customer_id"] == customer_id
    assert item["mapping_status"] == "mapped"

    created = client.post(
        f"/admin/churn-risks/predictions/{prediction_id}/intervention",
        headers=sales_headers,
        json={
            "action_type": "phone_call",
            "due_at": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
            "note": "先了解近期停课原因",
        },
    )
    assert created.status_code == 201
    intervention = created.json()
    assert intervention["status"] == "planned"
    assert intervention["note"] == "先了解近期停课原因"

    completed = client.patch(
        f"/admin/churn-risks/interventions/{intervention['id']}",
        headers=sales_headers,
        json={"status": "completed", "outcome": "recovered", "note": "家长同意继续学习"},
    )
    assert completed.status_code == 200
    assert completed.json()["outcome"] == "recovered"

    with SessionLocal() as db:
        schedule = db.get(Schedule, intervention["schedule_id"])
        assert schedule is not None
        assert schedule.status == "completed"
        assert schedule.outcome == "converted"
        timeline_types = set(
            db.scalars(
                select(TimelineEvent.event_type).where(TimelineEvent.customer_id == customer_id)
            ).all()
        )
        assert "churn_intervention_created" in timeline_types
        assert "churn_intervention_completed" in timeline_types

    duplicate = client.post(
        f"/admin/churn-risks/predictions/{prediction_id}/intervention",
        headers=sales_headers,
        json={
            "action_type": "phone_call",
            "due_at": (datetime.now(timezone.utc) + timedelta(days=2)).isoformat(),
        },
    )
    assert duplicate.status_code == 409

    # 本仓库的历史测试共享一个隔离数据库；移除本测试新增的 RESTRICT 映射，
    # 避免影响后续模块各自的清理逻辑。
    with SessionLocal() as db:
        db.execute(delete(ChurnRiskIntervention).where(ChurnRiskIntervention.prediction_id == prediction_id))
        db.execute(delete(ChurnRiskPrediction).where(ChurnRiskPrediction.id == prediction_id))
        db.execute(delete(ExternalStudentMapping).where(ExternalStudentMapping.student_id == student_id))
        db.execute(delete(ChurnScoringBatch).where(ChurnScoringBatch.id == batch_id))
        db.commit()
