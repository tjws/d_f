from app.integrations.operations.base import OperationsSyncProvider
from app.integrations.operations.mock_adapter import MockOperationsSyncProvider


def get_operations_sync_provider() -> OperationsSyncProvider:
    """当前只有 Mock；未来真实订单系统接入时替换此工厂。"""

    return MockOperationsSyncProvider()

