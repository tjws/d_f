from sqlalchemy import delete, func, select
from fastapi.testclient import TestClient

from app.db.session import SessionLocal
from app.main import app
from app.models.audit_log import AuditLog
from app.models.customer import Customer
from app.models.user import User


client = TestClient(app)


def setup_function():
    """清理本文件使用的测试用户和相关数据。"""

    with SessionLocal() as db:
        db.execute(delete(AuditLog))
        db.execute(delete(Customer))
        db.execute(delete(User))
        db.commit()


def test_mock_wecom_login_creates_and_reuses_user():
    """首次登录创建用户，重复登录复用同一用户。"""

    first_response = client.post(
        "/auth/wecom/mock",
        json={"code": "demo-code"},
    )

    assert first_response.status_code == 200
    assert first_response.json()["token_type"] == "bearer"

    with SessionLocal() as db:
        user = db.scalar(
            select(User).where(
                User.wecom_userid == "demo-user-001"
            )
        )
        user_id = user.id

    second_response = client.post(
        "/auth/wecom/mock",
        json={"code": "demo-code"},
    )

    assert second_response.status_code == 200

    with SessionLocal() as db:
        count = db.scalar(
            select(func.count(User.id)).where(
                User.wecom_userid == "demo-user-001"
            )
        )
        same_user = db.get(User, user_id)

    assert count == 1
    assert same_user.username == "demo_sales"


def test_mock_wecom_login_rejects_unknown_code():
    """未知 Mock 授权码返回 400。"""

    response = client.post(
        "/auth/wecom/mock",
        json={"code": "unknown-code"},
    )

    assert response.status_code == 400


def test_mock_wecom_login_is_disabled_in_real_mode(monkeypatch):
    """非 mock 模式下不能调用本地模拟登录。"""

    monkeypatch.setenv("WECOM_MODE", "wecom")

    response = client.post(
        "/auth/wecom/mock",
        json={"code": "demo-code"},
    )

    assert response.status_code == 404


def test_mock_wecom_login_rejects_username_collision():
    """本地用户名被占用时不能错误绑定企业微信身份。"""

    register_response = client.post(
        "/auth/register",
        json={
            "username": "demo_sales",
            "password": "Test123!",
        },
    )

    assert register_response.status_code == 201

    response = client.post(
        "/auth/wecom/mock",
        json={"code": "demo-code"},
    )

    assert response.status_code == 409


def test_mock_jwt_can_access_customer_api():
    """Mock 登录签发的 JWT 仍遵守本地客户权限。"""

    login_response = client.post(
        "/auth/wecom/mock",
        json={"code": "demo-code"},
    )
    assert login_response.status_code == 200

    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    create_response = client.post(
        "/customers",
        headers=headers,
        json={
            "name": "Mock 客户",
            "phone": "13800000004",
        },
    )

    assert create_response.status_code == 201

    list_response = client.get(
        "/customers",
        headers=headers,
    )

    assert list_response.status_code == 200
    assert list_response.json()["total"] == 1
    assert list_response.json()["items"][0]["name"] == "Mock 客户"
