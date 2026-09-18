"""知识库检索策略。

检索器只负责“找到候选资料”，本模块负责判断候选资料是否足够支持对客回复。
这样关键词检索、Qdrant 向量检索和后续的其他检索实现都可以共享同一条安全边界。
"""

from dataclasses import dataclass
import os
from typing import Literal

from sqlalchemy.orm import Session

from app.knowledge.retriever import KnowledgeDocument, search_knowledge


RetrievalMode = Literal["keyword", "vector", "mixed"]


def _env_int(name: str, default: int, minimum: int = 0) -> int:
    try:
        return max(minimum, int(os.getenv(name, str(default))))
    except (TypeError, ValueError):
        return default


def _env_float(name: str, default: float, minimum: float = 0.0) -> float:
    try:
        return max(minimum, float(os.getenv(name, str(default))))
    except (TypeError, ValueError):
        return default


def keyword_threshold() -> int:
    """关键词重叠数至少达到 2，避免只命中一个常见字就回答家长。"""

    return _env_int("RAG_MIN_KEYWORD_SCORE", 2, minimum=1)


def vector_threshold() -> float:
    """向量分数沿用 retriever 的 100 + cosine 约定，默认要求 cosine 至少约 0.35。"""

    return _env_float("RAG_MIN_VECTOR_SCORE", 100.35, minimum=100.0)


def fallback_message(consultant_name: str | None = None) -> str:
    """生成可直接交给顾问编辑的兜底话术，不对资料库之外的事实作承诺。"""

    name = (consultant_name or "当前顾问").strip() or "当前顾问"
    return f"暂时没有在已审核资料中找到足够依据，我是{name}，先为您核实后再回复。"


@dataclass(frozen=True)
class KnowledgeRetrievalResult:
    """经过安全阈值筛选后的知识结果及其可解释状态。"""

    hits: tuple[KnowledgeDocument, ...]
    matched: bool
    retrieval_mode: RetrievalMode
    threshold: float
    fallback_message: str | None
    query: str


def _item_threshold(item: KnowledgeDocument) -> float:
    return vector_threshold() if item.score >= 100.0 else float(keyword_threshold())


def _retrieval_mode(items: list[KnowledgeDocument]) -> RetrievalMode:
    has_vector = any(item.score >= 100.0 for item in items)
    has_keyword = any(item.score < 100.0 for item in items)
    if has_vector and has_keyword:
        return "mixed"
    if has_vector:
        return "vector"
    return "keyword"


def retrieve_knowledge(
    query: str,
    *,
    limit: int = 5,
    db: Session | None = None,
    use_vector: bool | None = None,
    consultant_name: str | None = None,
) -> KnowledgeRetrievalResult:
    """执行检索并只返回达到证据阈值的候选资料。"""

    normalized_query = query.strip()
    if not normalized_query or limit <= 0:
        return KnowledgeRetrievalResult((), False, "keyword", float(keyword_threshold()), None, normalized_query)

    candidates = search_knowledge(normalized_query, limit=limit, db=db, use_vector=use_vector)
    mode = _retrieval_mode(candidates)
    approved = tuple(item for item in candidates if item.score >= _item_threshold(item))
    effective_threshold = (
        min(_item_threshold(item) for item in approved)
        if approved
        else (vector_threshold() if mode == "vector" else float(keyword_threshold()))
    )
    return KnowledgeRetrievalResult(
        hits=approved,
        matched=bool(approved),
        retrieval_mode=mode,
        threshold=effective_threshold,
        fallback_message=None if approved else fallback_message(consultant_name),
        query=normalized_query,
    )


def should_use_fallback(context: dict[str, object]) -> bool:
    """只有存在实际询问且检索明确未命中时，才触发事实问答兜底。"""

    policy = context.get("knowledge_policy")
    return (
        isinstance(policy, dict)
        and bool(str(policy.get("query", "")).strip())
        and policy.get("matched") is False
    )


def fallback_reply_payload(
    context: dict[str, object],
    *,
    model_name: str,
    model_version: str,
) -> dict[str, object]:
    """返回不调用模型的人工可编辑草稿。"""

    policy = context.get("knowledge_policy")
    message = policy.get("fallback_message") if isinstance(policy, dict) else None
    return {
        "content": {
            "text": str(message or fallback_message()),
            "tone": "cautious",
            "purpose": "knowledge_fallback",
        },
        "evidence": [],
        "evidence_level": "insufficient",
        "model_name": model_name,
        "model_version": model_version,
    }


__all__ = [
    "KnowledgeRetrievalResult",
    "RetrievalMode",
    "fallback_message",
    "fallback_reply_payload",
    "keyword_threshold",
    "retrieve_knowledge",
    "should_use_fallback",
    "vector_threshold",
]
