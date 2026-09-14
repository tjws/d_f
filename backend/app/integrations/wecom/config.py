import os
from dataclasses import dataclass


@dataclass(frozen=True)
class WeComConfig:
    """企业微信运行配置；Secret 只从环境变量读取。"""

    mode: str
    corp_id: str | None
    agent_id: str | None
    secret: str | None
    callback_base_url: str | None
    callback_token: str | None

    @classmethod
    def from_env(cls) -> "WeComConfig":
        """读取环境变量；没有真实账号时默认使用 mock。"""

        return cls(
            mode=os.getenv("WECOM_MODE", "mock"),
            corp_id=os.getenv("WECOM_CORP_ID"),
            agent_id=os.getenv("WECOM_AGENT_ID"),
            secret=os.getenv("WECOM_SECRET"),
            callback_base_url=os.getenv("WECOM_CALLBACK_BASE_URL"),
            callback_token=os.getenv("WECOM_CALLBACK_TOKEN"),
        )
