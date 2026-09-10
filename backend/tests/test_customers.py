from fastapi.testclient import TestClient

from app.api.customers import _fake_customers
from app.main import app


# 使用 FastAPI 提供的测试客户端调用接口。
client = TestClient(app)


def setup_function():
    """每个测试开始前清空临时客户数据。"""

    _fake_customers.clear()


def test_create_and_get_customer():
    """测试创建客户和查询客户。"""

    payload = {
        "name": "测试家长",
        "phone": "13800138000",
        "student_name": "测试学生",
        "grade": "小学五年级",
        "interested_subject": "数学",
        "stage": "new",
        "source": "测试",
        "remark": "自动化测试",
    }

    create_response = client.post("/customers", json=payload)

    assert create_response.status_code == 201
    assert create_response.json()["name"] == "测试家长"

    get_response = client.get("/customers/1")

    assert get_response.status_code == 200
    assert get_response.json()["phone"] == "13800138000"


def test_update_customer():
    """测试部分修改客户。"""

    client.post(
        "/customers",
        json={
            "name": "测试家长",
            "phone": "13800138000",
        },
    )

    response = client.patch(
        "/customers/1",
        json={"remark": "已完成首次沟通"},
    )

    assert response.status_code == 200
    assert response.json()["remark"] == "已完成首次沟通"


def test_delete_customer():
    """测试删除客户。"""

    client.post(
        "/customers",
        json={
            "name": "测试家长",
            "phone": "13800138000",
        },
    )

    delete_response = client.delete("/customers/1")

    assert delete_response.status_code == 204

    get_response = client.get("/customers/1")

    assert get_response.status_code == 404