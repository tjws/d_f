from typing import Protocol


class OperationsSyncProvider(Protocol):
    def normalize(self, payload: dict) -> dict:
        """把外部订单/工单字段转换为本地契约。"""

