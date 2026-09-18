from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.db.session import SessionLocal
from app.main import app
from app.models.audit_log import AuditLog
from app.models.role_permission import RolePermission
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


def test_admin_can_read_and_update_permission_scope_with_audit_log():
    headers = _login_as("permission_matrix_admin", "admin")
    listed = client.get("/admin/permissions?role=manager&module=customers", headers=headers)
    assert listed.status_code == 200
    target = next(item for item in listed.json() if item["action"] == "read")
    original_scope = target["data_scope"]

    try:
        updated = client.patch(
            f"/admin/permissions/{target['id']}",
            headers=headers,
            json={"data_scope": "all"},
        )
        assert updated.status_code == 200
        assert updated.json()["data_scope"] == "all"
        with SessionLocal() as db:
            audit = db.scalar(
                select(AuditLog)
                .where(AuditLog.action == "permission.data_scope_changed")
                .order_by(AuditLog.id.desc())
            )
            assert audit is not None
            assert audit.target_id == str(target["id"])
    finally:
        # 测试结束恢复种子配置，避免影响同一进程中的其他测试。
        with SessionLocal() as db:
            permission = db.get(RolePermission, target["id"])
            if permission is not None:
                permission.data_scope = original_scope
            db.execute(delete(AuditLog).where(AuditLog.action == "permission.data_scope_changed"))
            db.commit()


def test_manager_can_read_permission_matrix_but_sales_cannot():
    manager_headers = _login_as("permission_matrix_manager", "manager")
    sales_headers = _login_as("permission_matrix_sales", "sales")
    assert client.get("/admin/permissions", headers=manager_headers).status_code == 200
    assert client.get("/admin/permissions", headers=sales_headers).status_code == 403


def test_admin_permission_update_keeps_admin_scope_and_validates_customer_scope():
    headers = _login_as("permission_guard_admin", "admin")
    admin_permissions = client.get("/admin/permissions?role=admin", headers=headers)
    assert admin_permissions.status_code == 200
    protected = next(item for item in admin_permissions.json() if item["module"] == "users" and item["action"] == "read")
    locked = client.patch(f"/admin/permissions/{protected['id']}", headers=headers, json={"data_scope": "own"})
    assert locked.status_code == 409

    customer_permissions = client.get("/admin/permissions?role=manager&module=customers", headers=headers)
    target = next(item for item in customer_permissions.json() if item["action"] == "read")
    invalid = client.patch(f"/admin/permissions/{target['id']}", headers=headers, json={"data_scope": "team"})
    assert invalid.status_code == 422
