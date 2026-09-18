import os

from app.ai.providers.base import (
    ProfileSuggestionProvider,
    ReplySuggestionProvider,
    ScheduleSuggestionProvider,
    TagSuggestionProvider,
)
from app.ai.providers.mock import MockReplyProvider
from app.ai.providers.mock_profile import MockProfileProvider
from app.ai.providers.mock_schedule import MockScheduleProvider
from app.ai.providers.mock_tag import MockTagProvider
from app.ai.providers.bailian import (
    BailianProfileProvider,
    BailianReplyProvider,
    BailianScheduleProvider,
    BailianTagProvider,
)


def _provider_name(setting_name: str) -> str:
    # 运行环境默认使用百炼；单元测试会显式设置 mock，避免测试误消耗额度。
    return os.getenv(setting_name, os.getenv("AI_PROVIDER", "bailian")).strip().lower()


def get_workflow_provider_name(goal: str, requires_profile: bool) -> str:
    """返回本次工作流实际可能调用的 Provider，用于成本限额而不泄露密钥。"""

    if goal == "profile":
        return _provider_name("AI_PROFILE_PROVIDER")
    if not requires_profile:
        return _provider_name("AI_PROFILE_PROVIDER")
    settings = {
        "reply": "AI_REPLY_PROVIDER",
        "tag": "AI_TAG_PROVIDER",
        "schedule": "AI_SCHEDULE_PROVIDER",
    }
    return _provider_name(settings.get(goal, "AI_REPLY_PROVIDER"))


def _unsupported_provider(setting_name: str, provider_name: str) -> ValueError:
    return ValueError(f"unsupported {setting_name}: {provider_name}")


def get_reply_provider() -> ReplySuggestionProvider:
    """根据环境配置选择回复 Provider；运行环境未配置时使用百炼。"""

    provider_name = _provider_name("AI_REPLY_PROVIDER")
    if provider_name == "mock":
        return MockReplyProvider()
    if provider_name == "bailian":
        return BailianReplyProvider()
    raise _unsupported_provider("AI_REPLY_PROVIDER", provider_name)


def get_profile_provider() -> ProfileSuggestionProvider:
    """根据环境配置选择客户画像 Provider；运行环境未配置时使用百炼。"""

    provider_name = _provider_name("AI_PROFILE_PROVIDER")
    if provider_name == "mock":
        return MockProfileProvider()
    if provider_name == "bailian":
        return BailianProfileProvider()
    raise _unsupported_provider("AI_PROFILE_PROVIDER", provider_name)


def get_tag_provider() -> TagSuggestionProvider:
    """根据环境配置选择标签 Provider；运行环境未配置时使用百炼。"""

    provider_name = _provider_name("AI_TAG_PROVIDER")
    if provider_name == "mock":
        return MockTagProvider()
    if provider_name == "bailian":
        return BailianTagProvider()
    raise _unsupported_provider("AI_TAG_PROVIDER", provider_name)


def get_schedule_provider() -> ScheduleSuggestionProvider:
    """根据环境配置选择日程 Provider；运行环境未配置时使用百炼。"""

    provider_name = _provider_name("AI_SCHEDULE_PROVIDER")
    if provider_name == "mock":
        return MockScheduleProvider()
    if provider_name == "bailian":
        return BailianScheduleProvider()
    raise _unsupported_provider("AI_SCHEDULE_PROVIDER", provider_name)
