import pytest

from app.integrations.wecom.adapter import WeComUserIdentity
from app.integrations.wecom.config import WeComConfig
from app.integrations.wecom.mock_adapter import MockWeComAdapter


def test_mock_adapter_returns_user_identity():
    """有效模拟授权码可以换取用户身份。"""

    adapter = MockWeComAdapter()

    identity = adapter.exchange_code_for_user("demo-code")

    assert identity == WeComUserIdentity(
        userid="demo-user-001",
        username="demo_sales",
        name="演示销售",
    )


def test_mock_adapter_rejects_unknown_code():
    """未知授权码不能换取身份。"""

    adapter = MockWeComAdapter()

    with pytest.raises(ValueError, match="无效的模拟授权码"):
        adapter.exchange_code_for_user("unknown-code")


def test_wecom_config_defaults_to_mock(monkeypatch):
    """没有真实账号配置时默认使用 mock。"""

    monkeypatch.delenv("WECOM_MODE", raising=False)

    config = WeComConfig.from_env()

    assert config.mode == "mock"
    assert config.secret is None