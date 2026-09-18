from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class WeComUserIdentity:
    """企业微信用户的最小身份信息。"""

    userid: str
    username: str
    name: str | None = None


class WeComAdapter(Protocol):
    """真实适配器和 Mock 适配器都要实现的接口。"""

    def exchange_code_for_user(
        self,
        code: str,
    ) -> WeComUserIdentity:
        """用授权码换取企业微信用户身份。"""

    def send_message(self, userid: str, content: str) -> str:
        """发送消息；返回外部消息编号。"""

    def create_calendar_event(self, userid: str, title: str, start_at: str) -> str:
        """创建日历事件；真实适配器以后实现。"""
