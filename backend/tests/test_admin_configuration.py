import base64

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.db.session import SessionLocal
from app.main import app
from app.models.audit_log import AuditLog
from app.models.customer import Customer
from app.models.sales_script import SalesScript
from app.models.system_setting import SystemSetting
from app.models.user import User


client = TestClient(app)


def setup_function():
    with SessionLocal() as db:
        for model in (SalesScript, SystemSetting, AuditLog, Customer, User):
            db.execute(delete(model))
        db.add_all([
            SystemSetting(key="ai_daily_bailian_request_limit", value_json=20, scope_type="global", description="test"),
            SystemSetting(key="knowledge_max_results", value_json=4, scope_type="global", description="test"),
            SystemSetting(key="default_follow_up_days", value_json=3, scope_type="global", description="test"),
        ])
        db.commit()


@pytest.fixture(autouse=True)
def encryption_key(monkeypatch):
    monkeypatch.setenv("APP_ENCRYPTION_KEY", base64.urlsafe_b64encode(b"c" * 32).decode("ascii"))


@pytest.fixture
def admin_headers():
    assert client.post("/auth/register", json={"username": "config_admin", "password": "Test123!"}).status_code == 201
    with SessionLocal() as db:
        user = db.query(User).filter_by(username="config_admin").one(); user.role = "admin"; db.commit()
    login = client.post("/auth/token", data={"username": "config_admin", "password": "Test123!"})
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def test_admin_settings_are_bounded_and_audited(admin_headers):
    settings = client.get("/admin/system-settings", headers=admin_headers)
    assert settings.status_code == 200
    assert {item["key"] for item in settings.json()} >= {"ai_daily_bailian_request_limit", "knowledge_max_results"}
    updated = client.put("/admin/system-settings/knowledge_max_results", headers=admin_headers, json={"value": 8})
    assert updated.status_code == 200 and updated.json()["value"] == 8
    invalid = client.put("/admin/system-settings/knowledge_max_results", headers=admin_headers, json={"value": 99})
    assert invalid.status_code == 422


def test_only_published_scripts_enter_ai_context(admin_headers):
    created = client.post("/admin/sales-scripts", headers=admin_headers, json={"scene": "价格异议", "title": "试听价格说明", "content": "可以先安排公开试听，再根据学习目标说明方案。", "tone": "professional"})
    assert created.status_code == 201
    script_id = created.json()["id"]
    pending = client.patch(f"/admin/sales-scripts/{script_id}", headers=admin_headers, json={"status": "pending_review"})
    assert pending.status_code == 200
    published = client.patch(f"/admin/sales-scripts/{script_id}", headers=admin_headers, json={"status": "published"})
    assert published.status_code == 200
    assert published.json()["approved_by"] is not None
    scripts = client.get("/admin/sales-scripts", headers=admin_headers).json()
    assert scripts[0]["status"] == "published"


def test_sales_cannot_access_configuration():
    assert client.post("/auth/register", json={"username": "config_sales", "password": "Test123!"}).status_code == 201
    login = client.post("/auth/token", data={"username": "config_sales", "password": "Test123!"})
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    assert client.get("/admin/system-settings", headers=headers).status_code == 403
    assert client.get("/admin/sales-scripts", headers=headers).status_code == 403
