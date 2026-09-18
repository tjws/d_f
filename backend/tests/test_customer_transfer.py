from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.db.session import SessionLocal
from app.main import app
from app.models.audit_log import AuditLog
from app.models.customer import Customer
from app.models.customer_transfer import CustomerTransfer
from app.models.organization import Organization
from app.models.student import Student
from app.models.user import User


client = TestClient(app)


def setup_function():
    with SessionLocal() as db:
        db.execute(delete(AuditLog)); db.execute(delete(CustomerTransfer)); db.execute(delete(Student)); db.execute(delete(Organization)); db.execute(delete(Customer)); db.execute(delete(User)); db.commit()


def _login(username: str) -> dict[str, str]:
    assert client.post("/auth/register", json={"username": username, "password": "Test123!"}).status_code == 201
    token = client.post("/auth/token", data={"username": username, "password": "Test123!"}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_admin_transfer_writes_history_and_audit():
    owner_headers = _login("transfer_owner")
    _login("transfer_target")
    with SessionLocal() as db:
        owner = db.query(User).filter_by(username="transfer_owner").one()
        owner.role = "admin"
        db.commit()
        target_id = db.query(User).filter_by(username="transfer_target").one().id

    customer = client.post("/customers", headers=owner_headers, json={"name": "待转移客户", "phone": "13800138000"})
    customer_id = customer.json()["id"]
    transferred = client.patch(f"/customers/{customer_id}/owner", headers=owner_headers, json={"to_user_id": target_id, "reason": "团队分配"})
    assert transferred.status_code == 200
    assert transferred.json()["owner_id"] == target_id
    history = client.get(f"/customers/{customer_id}/transfers", headers=owner_headers)
    assert history.status_code == 200
    assert history.json()[0]["to_user_id"] == target_id
    with SessionLocal() as db:
        assert db.query(AuditLog).filter_by(action="customer.transferred").count() == 1


def test_sales_cannot_transfer_customer():
    headers = _login("sales_transfer")
    customer_id = client.post("/customers", headers=headers, json={"name": "销售客户", "phone": "13800138001"}).json()["id"]
    _login("sales_target")
    with SessionLocal() as db:
        target_id = db.query(User).filter_by(username="sales_target").one().id
    response = client.patch(f"/customers/{customer_id}/owner", headers=headers, json={"to_user_id": target_id})
    assert response.status_code == 403
