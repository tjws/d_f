import base64

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.db.session import SessionLocal
from app.main import app
from app.models.audit_log import AuditLog
from app.models.customer import Customer
from app.models.organization import Organization
from app.models.student import Student
from app.models.user import User


client = TestClient(app)


def _key(seed: bytes = b"s" * 32) -> str:
    return base64.urlsafe_b64encode(seed).decode("ascii")


def setup_function():
    """每个学生接口测试前清理相关数据。"""

    with SessionLocal() as db:
        db.execute(delete(AuditLog))
        db.execute(delete(Student))
        db.execute(delete(Organization))
        db.execute(delete(Customer))
        db.execute(delete(User))
        db.commit()


@pytest.fixture(autouse=True)
def encryption_key(monkeypatch):
    monkeypatch.setenv("APP_ENCRYPTION_KEY", _key())


@pytest.fixture
def auth_headers():
    register = client.post(
        "/auth/register",
        json={
            "username": "student_owner",
            "password": "Test123!",
        },
    )
    assert register.status_code == 201

    login = client.post(
        "/auth/token",
        data={
            "username": "student_owner",
            "password": "Test123!",
        },
    )
    assert login.status_code == 200

    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _create_customer(headers: dict[str, str]) -> int:
    response = client.post(
        "/customers",
        headers=headers,
        json={
            "name": "学生测试客户",
            "phone": "13800138000",
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_create_and_list_students(auth_headers):
    customer_id = _create_customer(auth_headers)

    create_response = client.post(
        f"/customers/{customer_id}/students",
        headers=auth_headers,
        json={
            "name": "小明",
            "gender": "男",
            "grade": "五年级",
            "school": "实验小学",
            "subjects": {"数学": "重点关注"},
        },
    )

    assert create_response.status_code == 201
    body = create_response.json()
    assert body["name"] == "小明"
    assert body["school"] == "实验小学"
    assert body["subjects"] == {"数学": "重点关注"}
    assert "name_encrypted" not in body
    assert "school_encrypted" not in body

    with SessionLocal() as db:
        student = db.scalar(select(Student))
        assert student.name_encrypted != "小明"
        assert student.school_encrypted != "实验小学"

    list_response = client.get(
        f"/customers/{customer_id}/students",
        headers=auth_headers,
    )

    assert list_response.status_code == 200
    assert len(list_response.json()) == 1
    assert list_response.json()[0]["name"] == "小明"


def test_student_endpoints_require_authentication():
    response = client.get("/customers/1/students")

    assert response.status_code == 401


def test_user_cannot_access_another_users_students(auth_headers):
    customer_id = _create_customer(auth_headers)

    other_register = client.post(
        "/auth/register",
        json={
            "username": "other_student_user",
            "password": "Test123!",
        },
    )
    assert other_register.status_code == 201

    other_login = client.post(
        "/auth/token",
        data={
            "username": "other_student_user",
            "password": "Test123!",
        },
    )
    other_headers = {
        "Authorization": f"Bearer {other_login.json()['access_token']}"
    }

    get_response = client.get(
        f"/customers/{customer_id}/students",
        headers=other_headers,
    )
    create_response = client.post(
        f"/customers/{customer_id}/students",
        headers=other_headers,
        json={"name": "越权学生"},
    )

    assert get_response.status_code == 404
    assert create_response.status_code == 404
