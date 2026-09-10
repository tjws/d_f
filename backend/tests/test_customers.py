from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.db.session import SessionLocal
from app.main import app
from app.models.customer import Customer


client = TestClient(app)


def setup_function():
    """每个测试前清空 customers 表，保证测试互不影响。"""

    with SessionLocal() as db:
        db.execute(delete(Customer))
        db.commit()


def test_create_and_get_customer():
    """测试创建客户和查询客户。"""

    response = client.post(
        "/customers",
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

    get_response = client.get(f"/customers/{customer_id}")

    assert get_response.status_code == 200
    assert get_response.json()["name"] == "测试家长"


def test_update_customer():
    """测试修改客户。"""

    response = client.post(
        "/customers",
        json={
            "name": "测试家长",
            "phone": "13800138000",
        },
    )

    customer_id = response.json()["id"]

    update_response = client.patch(
        f"/customers/{customer_id}",
        json={"remark": "已完成首次沟通"},
    )

    assert update_response.status_code == 200
    assert update_response.json()["remark"] == "已完成首次沟通"


def test_delete_customer():
    """测试删除客户。"""

    response = client.post(
        "/customers",
        json={
            "name": "测试家长",
            "phone": "13800138000",
        },
    )

    customer_id = response.json()["id"]

    delete_response = client.delete(f"/customers/{customer_id}")

    assert delete_response.status_code == 204

    get_response = client.get(f"/customers/{customer_id}")

    assert get_response.status_code == 404