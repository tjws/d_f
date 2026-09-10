import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.db.session import SessionLocal
from app.main import app
from app.models.customer import Customer
from app.models.user import User


client = TestClient(app)


def setup_function():
    """每个测试前清空测试数据。"""

    with SessionLocal() as db:
        db.execute(delete(Customer))
        db.execute(delete(User))
        db.commit()


@pytest.fixture
def auth_headers():
    """创建测试用户并返回 Bearer Token 请求头。"""

    register_response = client.post(
        "/auth/register",
        json={
            "username": "testuser",
            "password": "Test123!",
            "full_name": "测试用户",
        },
    )

    assert register_response.status_code == 201

    login_response = client.post(
        "/auth/token",
        data={
            "username": "testuser",
            "password": "Test123!",
        },
    )

    assert login_response.status_code == 200

    token = login_response.json()["access_token"]

    return {
        "Authorization": f"Bearer {token}",
    }


def test_create_and_get_customer(auth_headers):
    """测试登录后创建和查询客户。"""

    response = client.post(
        "/customers",
        headers=auth_headers,
        json={
            "name": "测试家长",
            "phone": "13800138000",
            "student_name": "测试学生",
            "grade": "小学五年级",
            "interested_subject": "数学",
            "stage": "new",
            "source": "测试",
            "remark": "自动化测试",
        },
    )

    assert response.status_code == 201

    customer_id = response.json()["id"]

    get_response = client.get(
        f"/customers/{customer_id}",
        headers=auth_headers,
    )

    assert get_response.status_code == 200


def test_update_customer(auth_headers):
    """测试登录后修改客户。"""

    response = client.post(
        "/customers",
        headers=auth_headers,
        json={
            "name": "测试家长",
            "phone": "13800138000",
        },
    )

    customer_id = response.json()["id"]

    update_response = client.patch(
        f"/customers/{customer_id}",
        headers=auth_headers,
        json={"remark": "已完成首次沟通"},
    )

    assert update_response.status_code == 200


def test_delete_customer(auth_headers):
    """测试登录后删除客户。"""

    response = client.post(
        "/customers",
        headers=auth_headers,
        json={
            "name": "测试家长",
            "phone": "13800138000",
        },
    )

    customer_id = response.json()["id"]

    delete_response = client.delete(
        f"/customers/{customer_id}",
        headers=auth_headers,
    )

    assert delete_response.status_code == 204


def _register_and_login(username: str) -> dict:
    """注册指定用户，并返回 Bearer Token 请求头。"""

    register_response = client.post(
        "/auth/register",
        json={
            "username": username,
            "password": "Test123!",
        },
    )

    assert register_response.status_code == 201

    login_response = client.post(
        "/auth/token",
        data={
            "username": username,
            "password": "Test123!",
        },
    )

    assert login_response.status_code == 200

    return {
        "Authorization": f"Bearer {login_response.json()['access_token']}",
    }


def test_customers_require_authentication():
    """未登录用户不能访问客户接口。"""

    response = client.get("/customers")

    assert response.status_code == 401


def test_user_cannot_access_another_users_customer(auth_headers):
    """普通销售不能访问、修改或删除其他用户负责的客户。"""

    create_response = client.post(
        "/customers",
        headers=auth_headers,
        json={
            "name": "用户 A 的客户",
            "phone": "13800138000",
        },
    )

    assert create_response.status_code == 201
    customer_id = create_response.json()["id"]

    another_user_headers = _register_and_login("another_user")

    get_response = client.get(
        f"/customers/{customer_id}",
        headers=another_user_headers,
    )
    assert get_response.status_code == 404

    update_response = client.patch(
        f"/customers/{customer_id}",
        headers=another_user_headers,
        json={"remark": "越权修改"},
    )
    assert update_response.status_code == 404

    delete_response = client.delete(
        f"/customers/{customer_id}",
        headers=another_user_headers,
    )
    assert delete_response.status_code == 404
