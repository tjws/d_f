from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.db.session import SessionLocal
from app.main import app
from app.models.audit_log import AuditLog
from app.models.customer import Customer
from app.models.customer_tag import CustomerTag
from app.models.tag import Tag
from app.models.user import User


client = TestClient(app)


def setup_function():
    with SessionLocal() as db:
        for model in (CustomerTag, Tag, AuditLog, Customer, User):
            db.execute(delete(model))
        db.commit()


def _login_as(username: str, role: str) -> dict[str, str]:
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


def test_admin_tag_directory_can_be_managed_and_statistics_are_visible():
    admin_headers = _login_as("tag_admin", "admin")
    created = client.post(
        "/admin/tags",
        headers=admin_headers,
        json={"key": "high_intent", "name": "高意向", "category": "意向度", "description": "近期可能转化"},
    )
    assert created.status_code == 201
    tag_id = created.json()["id"]

    with SessionLocal() as db:
        admin = db.scalar(select(User).where(User.username == "tag_admin"))
        customer = Customer(owner_id=admin.id, name="标签统计客户", phone="13800138009")
        db.add(customer)
        db.flush()
        db.add(CustomerTag(customer_id=customer.id, tag_id=tag_id, source="ai", status="confirmed"))
        db.commit()

    listed = client.get("/admin/tags", headers=admin_headers)
    assert listed.status_code == 200
    row = next(item for item in listed.json() if item["id"] == tag_id)
    assert row["customer_count"] == 1
    assert row["confirmed_count"] == 1

    updated = client.patch(f"/admin/tags/{tag_id}", headers=admin_headers, json={"status": "inactive", "name": "重点客户"})
    assert updated.status_code == 200
    assert updated.json()["status"] == "inactive"
    assert updated.json()["name"] == "重点客户"


def test_tag_directory_allows_manager_read_only_and_denies_sales():
    manager_headers = _login_as("tag_manager", "manager")
    sales_headers = _login_as("tag_sales", "sales")
    assert client.get("/admin/tags", headers=manager_headers).status_code == 200
    assert client.post("/admin/tags", headers=manager_headers, json={"key": "manager_tag", "name": "经理标签", "category": "测试"}).status_code == 403
    assert client.get("/admin/tags", headers=sales_headers).status_code == 403
