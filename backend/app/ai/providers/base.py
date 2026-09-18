from typing import Protocol, TypedDict


class EmbeddingProvider(Protocol):
    """文本向量 Provider；默认实现必须是本地 Mock。"""

    model_name: str

    def embed(self, texts: list[str]) -> list[list[float]]:
        """将文本转换为固定维度向量，不负责写入向量数据库。"""


class ReplySuggestionPayload(TypedDict):
    """回复 Provider 的统一输出，不包含数据库状态字段。"""

    content: dict[str, object]
    evidence: list[dict[str, object]]
    evidence_level: str
    model_name: str
    model_version: str


class ReplySuggestionProvider(Protocol):
    """所有回复生成实现都要遵守的最小接口。"""

    def generate(self, context: dict[str, object]) -> ReplySuggestionPayload:
        """根据脱敏客户上下文生成一条待人工确认的回复草稿。"""


class ProfileSuggestionPayload(TypedDict):
    """客户画像 Provider 的统一输出。"""

    dimensions: dict[str, object]
    evidence: list[dict[str, object]]
    model_name: str
    model_version: str


class ProfileSuggestionProvider(Protocol):
    """所有客户画像生成实现都要遵守的最小接口。"""

    def generate(self, context: dict[str, object]) -> ProfileSuggestionPayload:
        """根据脱敏客户上下文生成画像草稿内容和证据。"""


class TagSuggestionCandidate(TypedDict):
    """一条待人工确认的标签候选项。"""

    key: str
    name: str
    category: str
    description: str
    color: str
    evidence: list[dict[str, object]]


class TagSuggestionPayload(TypedDict):
    """标签 Provider 的统一输出。"""

    candidates: list[TagSuggestionCandidate]
    model_name: str
    model_version: str


class TagSuggestionProvider(Protocol):
    """所有标签推荐实现都要遵守的最小接口。"""

    def generate(self, context: dict[str, object]) -> TagSuggestionPayload:
        """根据客户和已确认画像生成待确认标签。"""


class ScheduleSuggestionPayload(TypedDict):
    """日程 Provider 的统一输出。"""

    content: dict[str, object]
    evidence: list[dict[str, object]]
    evidence_level: str
    model_name: str
    model_version: str


class ScheduleSuggestionProvider(Protocol):
    """所有日程建议实现都要遵守的最小接口。"""

    def generate(self, context: dict[str, object]) -> ScheduleSuggestionPayload:
        """根据已确认画像和客户上下文生成待确认日程。"""
