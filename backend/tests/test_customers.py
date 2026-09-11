import sys

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select

from app.db.session import SessionLocal
from app.main import app
from app.models.audit_log import AuditLog
from app.models.customer import Customer
from app.models.organization import Organization
from app.models.user import User
from scripts import promote_user


client = TestClient(app)


def setup_function():
    """每个测试前清空测试数据。"""

    with SessionLocal() as db:
        # 先清理审计日志，避免旧记录影响当前测试。
        db.execute(delete(AuditLog))
        db.execute(delete(Organization))
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


@pytest.fixture
def admin_headers():
    """创建测试管理员并返回 Bearer Token 请求头。"""

    headers = _register_and_login("adminuser")

    # 测试中直接设置角色，模拟受控的管理员初始化流程。
    with SessionLocal() as db:
        admin_user = db.scalar(
            select(User).where(User.username == "adminuser")
        )
        admin_user.role = "admin"
        db.commit()

    return headers


def test_sales_cannot_manage_users(auth_headers):
    """普通销售不能查看用户管理接口。"""

    response = client.get(
        "/users",
        headers=auth_headers,
    )

    assert response.status_code == 403


def test_manager_cannot_update_user_role():
    """经理可以查看用户，但不能修改用户角色。"""

    manager_headers = _register_and_login("manageruser")
    _register_and_login("manager_target")

    with SessionLocal() as db:
        manager_user = db.scalar(
            select(User).where(User.username == "manageruser")
        )
        target_user = db.scalar(
            select(User).where(User.username == "manager_target")
        )
        target_user_id = target_user.id
        manager_user.role = "manager"
        db.commit()

    response = client.patch(
        f"/users/{target_user_id}/role",
        headers=manager_headers,
        json={"role": "admin"},
    )

    assert response.status_code == 403


def test_admin_can_create_and_assign_organization(admin_headers):
    """管理员可以创建组织树并为用户分配组织。"""

    _register_and_login("organization_target")

    root_response = client.post(
        "/organizations",
        headers=admin_headers,
        json={"name": "总部", "type": "group"},
    )

    assert root_response.status_code == 201
    root = root_response.json()
    assert root["parent_id"] is None
    assert root["path"] == f"/{root['id']}"

    child_response = client.post(
        "/organizations",
        headers=admin_headers,
        json={
            "name": "华东区域",
            "type": "region",
            "parent_id": root["id"],
        },
    )

    assert child_response.status_code == 201
    child = child_response.json()
    assert child["path"] == f"/{root['id']}/{child['id']}"

    organizations_response = client.get(
        "/organizations",
        headers=admin_headers,
    )
    assert organizations_response.status_code == 200
    assert len(organizations_response.json()) == 2

    users_response = client.get(
        "/users",
        headers=admin_headers,
    )
    target_user = next(
        user
        for user in users_response.json()
        if user["username"] == "organization_target"
    )

    assign_response = client.patch(
        f"/users/{target_user['id']}/organization",
        headers=admin_headers,
        json={"organization_id": child["id"]},
    )

    assert assign_response.status_code == 200
    assert assign_response.json()["organization_id"] == child["id"]

    with SessionLocal() as db:
        audit_log = db.scalar(
            select(AuditLog)
            .where(
                AuditLog.action == "user.organization_changed",
                AuditLog.target_id == str(target_user["id"]),
            )
            .order_by(AuditLog.id.desc())
        )

    assert audit_log is not None
    assert audit_log.detail_json == {
        "before": {"organization_id": None},
        "after": {"organization_id": child["id"]},
    }


def test_sales_cannot_create_organization(auth_headers):
    """普通销售不能创建组织。"""

    response = client.post(
        "/organizations",
        headers=auth_headers,
        json={"name": "越权组织", "type": "team"},
    )

    assert response.status_code == 403


def test_admin_can_query_audit_logs_and_sales_cannot(
    admin_headers,
    auth_headers,
):
    """管理员可以查询审计日志，普通销售不能查询。"""

    create_response = client.post(
        "/organizations",
        headers=admin_headers,
        json={"name": "审计测试组织", "type": "team"},
    )
    assert create_response.status_code == 201

    admin_response = client.get(
        "/audit-logs",
        headers=admin_headers,
        params={
            "action": "organization.created",
            "page": 1,
            "page_size": 10,
        },
    )

    assert admin_response.status_code == 200
    body = admin_response.json()
    assert body["total"] == 1
    assert len(body["items"]) == 1
    assert body["items"][0]["action"] == "organization.created"
    assert body["items"][0]["actor_username_snapshot"] == "adminuser"

    sales_response = client.get(
        "/audit-logs",
        headers=auth_headers,
    )
    assert sales_response.status_code == 403


def test_admin_can_list_and_update_user_role(admin_headers):
    """管理员可以查看用户并修改其他用户角色。"""

    _register_and_login("targetuser")

    users_response = client.get(
        "/users",
        headers=admin_headers,
    )

    assert users_response.status_code == 200

    target_user = next(
        user
        for user in users_response.json()
        if user["username"] == "targetuser"
    )

    update_response = client.patch(
        f"/users/{target_user['id']}/role",
        headers=admin_headers,
        json={"role": "manager"},
    )

    assert update_response.status_code == 200
    assert update_response.json()["role"] == "manager"

    with SessionLocal() as db:
        audit_log = db.scalar(
            select(AuditLog)
            .where(
                AuditLog.action == "user.role_changed",
                AuditLog.target_type == "user",
                AuditLog.target_id == str(target_user["id"]),
            )
            .order_by(AuditLog.id.desc())
        )

    assert audit_log is not None
    assert audit_log.actor_role_snapshot == "admin"
    assert audit_log.detail_json == {
        "before": {"role": "sales"},
        "after": {"role": "manager"},
    }


def test_admin_cannot_demote_self(admin_headers):
    """管理员不能把自己的角色降级。"""

    users_response = client.get(
        "/users",
        headers=admin_headers,
    )

    admin_user = next(
        user
        for user in users_response.json()
        if user["username"] == "adminuser"
    )

    response = client.patch(
        f"/users/{admin_user['id']}/role",
        headers=admin_headers,
        json={"role": "sales"},
    )

    assert response.status_code == 400


def test_promote_script_requires_operator_for_regular_change(monkeypatch):
    """普通角色修改必须提供操作者。"""

    _register_and_login("script_admin")

    with SessionLocal() as db:
        admin_user = db.scalar(
            select(User).where(User.username == "script_admin")
        )
        admin_user.role = "admin"
        db.commit()

    monkeypatch.setattr(
        sys,
        "argv",
        ["promote_user.py", "script_admin", "sales"],
    )

    with pytest.raises(
        SystemExit,
        match="普通角色修改必须提供 --operator",
    ):
        promote_user.main()

    with SessionLocal() as db:
        admin_user = db.scalar(
            select(User).where(User.username == "script_admin")
        )
        assert admin_user.role == "admin"


def test_promote_script_can_demote_when_another_admin_exists(monkeypatch):
    """存在其他管理员时，维护脚本可以降级目标用户。"""

    _register_and_login("script_admin_one")
    _register_and_login("script_admin_two")

    with SessionLocal() as db:
        users = db.scalars(
            select(User).where(
                User.username.in_(
                    ["script_admin_one", "script_admin_two"]
                )
            )
        ).all()

        for user in users:
            user.role = "admin"

        db.commit()

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "promote_user.py",
            "script_admin_two",
            "manager",
            "--operator",
            "script_admin_one",
        ],
    )

    promote_user.main()

    with SessionLocal() as db:
        target_user = db.scalar(
            select(User).where(User.username == "script_admin_two")
        )
        operator_user = db.scalar(
            select(User).where(User.username == "script_admin_one")
        )
        assert target_user.role == "manager"

        audit_log = db.scalar(
            select(AuditLog).where(
                AuditLog.action == "user.role_changed",
                AuditLog.target_id == str(target_user.id),
            )
        )

        assert audit_log is not None
        assert audit_log.actor_user_id == operator_user.id
        assert audit_log.actor_username_snapshot == "script_admin_one"
        assert audit_log.actor_source == "maintenance_script"
        assert audit_log.detail_json == {
            "before": {"role": "admin"},
            "after": {"role": "manager"},
        }


def test_promote_script_bootstrap_writes_audit_log(monkeypatch):
    """bootstrap 初始化管理员时记录维护脚本审计日志。"""

    _register_and_login("bootstrap_user")

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "promote_user.py",
            "bootstrap_user",
            "admin",
            "--bootstrap",
        ],
    )

    promote_user.main()

    with SessionLocal() as db:
        target_user = db.scalar(
            select(User).where(User.username == "bootstrap_user")
        )
        audit_log = db.scalar(
            select(AuditLog).where(
                AuditLog.action == "user.role_changed",
                AuditLog.target_id == str(target_user.id),
            )
        )

    assert target_user.role == "admin"
    assert audit_log is not None
    assert audit_log.actor_user_id is None
    assert audit_log.actor_source == "maintenance_script_bootstrap"


def test_promote_script_does_not_log_when_role_is_unchanged(monkeypatch):
    """目标角色未变化时不新增审计日志。"""

    _register_and_login("script_operator")
    _register_and_login("unchanged_user")

    with SessionLocal() as db:
        operator_user = db.scalar(
            select(User).where(User.username == "script_operator")
        )
        operator_user.role = "admin"
        db.commit()

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "promote_user.py",
            "unchanged_user",
            "sales",
            "--operator",
            "script_operator",
        ],
    )

    promote_user.main()

    with SessionLocal() as db:
        audit_count = db.scalar(
            select(func.count(AuditLog.id))
            .where(AuditLog.action == "user.role_changed")
        )

    assert audit_count == 0


def test_manager_sees_only_customers_in_own_organization(
    admin_headers,
):
    """经理只能看到自己组织负责人的客户。"""

    manager_headers = _register_and_login("scope_manager")
    sales_a_headers = _register_and_login("scope_sales_a")
    sales_b_headers = _register_and_login("scope_sales_b")

    with SessionLocal() as db:
        manager_user = db.scalar(
            select(User).where(User.username == "scope_manager")
        )
        manager_user.role = "manager"
        db.commit()

    org_a_response = client.post(
        "/organizations",
        headers=admin_headers,
        json={"name": "组织 A", "type": "team"},
    )
    org_b_response = client.post(
        "/organizations",
        headers=admin_headers,
        json={"name": "组织 B", "type": "team"},
    )

    assert org_a_response.status_code == 201
    assert org_b_response.status_code == 201

    org_a_id = org_a_response.json()["id"]
    org_b_id = org_b_response.json()["id"]

    users = client.get(
        "/users",
        headers=admin_headers,
    ).json()

    user_ids = {
        user["username"]: user["id"]
        for user in users
        if user["username"]
        in {
            "scope_manager",
            "scope_sales_a",
            "scope_sales_b",
        }
    }

    assignments = {
        "scope_manager": org_a_id,
        "scope_sales_a": org_a_id,
        "scope_sales_b": org_b_id,
    }

    for username, organization_id in assignments.items():
        response = client.patch(
            f"/users/{user_ids[username]}/organization",
            headers=admin_headers,
            json={"organization_id": organization_id},
        )
        assert response.status_code == 200

    own_customer = client.post(
        "/customers",
        headers=sales_a_headers,
        json={
            "name": "组织 A 客户",
            "phone": "13800000001",
        },
    )
    other_customer = client.post(
        "/customers",
        headers=sales_b_headers,
        json={
            "name": "组织 B 客户",
            "phone": "13800000002",
        },
    )

    assert own_customer.status_code == 201
    assert other_customer.status_code == 201

    response = client.get(
        "/customers",
        headers=manager_headers,
    )

    assert response.status_code == 200

    visible_names = {
        item["name"]
        for item in response.json()["items"]
    }

    assert "组织 A 客户" in visible_names
    assert "组织 B 客户" not in visible_names


def test_manager_cannot_access_other_organization_customer(
    admin_headers,
):
    """经理不能查看、修改或删除其他组织的客户。"""

    manager_headers = _register_and_login("detail_scope_manager")
    sales_headers = _register_and_login("detail_scope_sales")

    with SessionLocal() as db:
        manager_user = db.scalar(
            select(User).where(User.username == "detail_scope_manager")
        )
        manager_user.role = "manager"
        db.commit()

    manager_org_response = client.post(
        "/organizations",
        headers=admin_headers,
        json={"name": "经理组织", "type": "team"},
    )
    sales_org_response = client.post(
        "/organizations",
        headers=admin_headers,
        json={"name": "销售组织", "type": "team"},
    )

    assert manager_org_response.status_code == 201
    assert sales_org_response.status_code == 201

    manager_org_id = manager_org_response.json()["id"]
    sales_org_id = sales_org_response.json()["id"]

    users = client.get(
        "/users",
        headers=admin_headers,
    ).json()
    user_ids = {
        user["username"]: user["id"]
        for user in users
        if user["username"]
        in {"detail_scope_manager", "detail_scope_sales"}
    }

    for username, organization_id in {
        "detail_scope_manager": manager_org_id,
        "detail_scope_sales": sales_org_id,
    }.items():
        response = client.patch(
            f"/users/{user_ids[username]}/organization",
            headers=admin_headers,
            json={"organization_id": organization_id},
        )
        assert response.status_code == 200

    customer_response = client.post(
        "/customers",
        headers=sales_headers,
        json={
            "name": "其他组织客户",
            "phone": "13800000003",
        },
    )
    assert customer_response.status_code == 201
    customer_id = customer_response.json()["id"]

    get_response = client.get(
        f"/customers/{customer_id}",
        headers=manager_headers,
    )
    update_response = client.patch(
        f"/customers/{customer_id}",
        headers=manager_headers,
        json={"remark": "越权修改"},
    )
    delete_response = client.delete(
        f"/customers/{customer_id}",
        headers=manager_headers,
    )

    assert get_response.status_code == 404
    assert update_response.status_code == 404
    assert delete_response.status_code == 404

    owner_response = client.get(
        f"/customers/{customer_id}",
        headers=sales_headers,
    )
    assert owner_response.status_code == 200
    assert owner_response.json()["remark"] is None
