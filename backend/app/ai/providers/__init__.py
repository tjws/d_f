"""AI 模型 Provider 适配层。"""

from app.ai.providers.base import (
    ProfileSuggestionPayload,
    ProfileSuggestionProvider,
    ReplySuggestionPayload,
    ReplySuggestionProvider,
    ScheduleSuggestionPayload,
    ScheduleSuggestionProvider,
    TagSuggestionCandidate,
    TagSuggestionPayload,
    TagSuggestionProvider,
)
from app.ai.providers.factory import (
    get_profile_provider,
    get_reply_provider,
    get_schedule_provider,
    get_tag_provider,
)
from app.ai.providers.bailian import (
    BailianProfileProvider,
    BailianProviderError,
    BailianReplyProvider,
    BailianScheduleProvider,
    BailianTagProvider,
)
from app.ai.providers.mock import MockReplyProvider
from app.ai.providers.mock_profile import MockProfileProvider
from app.ai.providers.mock_schedule import MockScheduleProvider
from app.ai.providers.mock_tag import MockTagProvider

__all__ = [
    "MockReplyProvider",
    "MockProfileProvider",
    "MockScheduleProvider",
    "MockTagProvider",
    "BailianProfileProvider",
    "BailianProviderError",
    "BailianReplyProvider",
    "BailianScheduleProvider",
    "BailianTagProvider",
    "ProfileSuggestionPayload",
    "ProfileSuggestionProvider",
    "ReplySuggestionPayload",
    "ReplySuggestionProvider",
    "ScheduleSuggestionPayload",
    "ScheduleSuggestionProvider",
    "TagSuggestionCandidate",
    "TagSuggestionPayload",
    "TagSuggestionProvider",
    "get_profile_provider",
    "get_reply_provider",
    "get_schedule_provider",
    "get_tag_provider",
]
