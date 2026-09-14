from app.integrations.wecom.adapter import (
    WeComAdapter,
    WeComUserIdentity,
)


class MockWeComAdapter:
    """本地开发使用的企业微信模拟适配器。"""

    def __init__(
        self,
        identities: dict[str, WeComUserIdentity] | None = None,
    ):
        self.identities = identities or {
            "demo-code": WeComUserIdentity(
                userid="demo-user-001",
                username="demo_sales",
                name="演示销售",
            )
        }

    def exchange_code_for_user(
        self,
        code: str,
    ) -> WeComUserIdentity:
        """模拟授权码换身份；未知授权码直接失败。"""

        identity = self.identities.get(code)

        if identity is None:
            raise ValueError("无效的模拟授权码")

        return identity