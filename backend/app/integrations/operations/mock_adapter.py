class MockOperationsSyncProvider:
    """本地演练适配器：只接受请求中的固定结构，不访问外部网络。"""

    def normalize(self, payload: dict) -> dict:
        return {
            "orders": list(payload.get("orders", [])),
            "tickets": list(payload.get("tickets", [])),
        }

