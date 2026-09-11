from app.core.permissions import get_data_scope, has_permission
from app.db.session import SessionLocal
from app.models.user import User


def test_sales_customer_read_uses_own_scope():
    """销售读取客户时使用 own 数据范围。"""

    with SessionLocal() as db:
        user = User(role="sales")

        assert get_data_scope(
            db,
            user,
            "customers",
            "read",
        ) == "own"
        assert has_permission(
            db,
            user,
            "customers",
            "read",
        ) is True


def test_manager_customer_read_uses_organization_scope():
    """经理读取客户时使用 organization 数据范围。"""

    with SessionLocal() as db:
        user = User(role="manager")

        assert get_data_scope(
            db,
            user,
            "customers",
            "read",
        ) == "organization"


def test_sales_cannot_read_user_management():
    """没有权限配置时返回无权限。"""

    with SessionLocal() as db:
        user = User(role="sales")

        assert get_data_scope(
            db,
            user,
            "users",
            "read",
        ) is None
        assert has_permission(
            db,
            user,
            "users",
            "read",
        ) is False
