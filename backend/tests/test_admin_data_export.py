from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.session import SessionLocal
from app.main import app
from app.models.audit_log import AuditLog
from app.models.user import User


client = TestClient(app)


def _login_as(username: str, role: str) -> dict[str, str]:
    password = "Test123!"
    registered = client.post("/auth/register", json={"username": username, "password": password})
    assert registered.status_code == 201
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.username == username))
        assert user is not None
        user.role = role
        db.commit()
    login = client.post("/auth/token", data={"username": username, "password": password})
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def test_admin_can_download_redacted_customer_export_and_policy():
    headers = _login_as("export_admin", "admin")
    customer = client.post(
        "/customers",
        headers=headers,
        json={"name": "张三", "phone": "13800138000", "student_name": "张小三"},
    )
    assert customer.status_code == 201

    policy = client.get("/admin/data-export/policy", headers=headers)
    assert policy.status_code == 200
    assert policy.json()["automatic_deletion_enabled"] is False
    assert policy.json()["default_export_redacted"] is True

    exported = client.get("/admin/data-export/customers?format=csv", headers=headers)
    assert exported.status_code == 200
    assert "attachment" in exported.headers["content-disposition"]
    body = exported.content.decode("utf-8-sig")
    assert "张*" in body
    assert "138****8000" in body
    assert "13800138000" not in body

    with SessionLocal() as db:
        audit = db.scalar(
            select(AuditLog)
            .where(AuditLog.action == "admin.data_exported")
            .order_by(AuditLog.id.desc())
        )
        assert audit is not None
        assert audit.target_id == "customers"
        assert audit.detail_json["redacted"] is True


def test_data_export_requires_admin_and_validates_date_range():
    manager_headers = _login_as("export_manager", "manager")
    sales_headers = _login_as("export_sales", "sales")
    assert client.get("/admin/data-export/policy", headers=manager_headers).status_code == 403
    assert client.get("/admin/data-export/customers", headers=sales_headers).status_code == 403

    admin_headers = _login_as("export_range_admin", "admin")
    invalid = client.get(
        "/admin/data-export/customers?start=2026-09-20T00:00:00Z&end=2026-09-19T00:00:00Z",
        headers=admin_headers,
    )
    assert invalid.status_code == 422
