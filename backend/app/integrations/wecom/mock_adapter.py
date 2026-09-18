from app.integrations.wecom.adapter import (
    WeComAdapter,
    WeComUserIdentity,
)
from datetime import datetime, timezone


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

    def send_message(self, userid: str, content: str) -> str:
        """仅生成可追踪的 Mock 编号，不访问外部网络。"""
        if not userid or not content.strip():
            raise ValueError("Mock 消息需要 userid 和 content")
        return f"mock-out-{userid}-{int(datetime.now(timezone.utc).timestamp() * 1000)}"

    def create_calendar_event(self, userid: str, title: str, start_at: str) -> str:
        """仅返回本地日历编号，正式日程仍由人工确认后写入数据库。"""
        if not userid or not title.strip() or not start_at.strip():
            raise ValueError("Mock 日历需要 userid、title 和 start_at")
        return f"mock-calendar-{userid}-{int(datetime.now(timezone.utc).timestamp() * 1000)}"
