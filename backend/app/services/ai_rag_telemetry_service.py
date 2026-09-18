"""RAG 检索遥测的写入服务。

这里只记录截断后的查询摘要和检索结果，不保存完整聊天正文或模型密钥。
"""

from typing import Any

from sqlalchemy.orm import Session

from app.models.ai_rag_interaction import AIRagInteraction


def _query_excerpt(query: str | None) -> str | None:
    value = str(query or "").strip()
    return value[:240] or None


def record_rag_interaction(
    db: Session,
    *,
    customer_id: int | None,
    actor_user_id: int | None,
    run_id: int | None,
    suggestion_id: int | None,
    entrypoint: str,
    query: str | None,
    retrieval_mode: str,
    matched: bool,
    fallback: bool,
    duration_ms: int | None = None,
    metadata: dict[str, Any] | None = None,
) -> AIRagInteraction:
    """加入当前事务，提交动作由调用方统一控制。"""

    interaction = AIRagInteraction(
        customer_id=customer_id,
        actor_user_id=actor_user_id,
        run_id=run_id,
        suggestion_id=suggestion_id,
        entrypoint=entrypoint[:30],
        query_excerpt=_query_excerpt(query),
        retrieval_mode=(retrieval_mode or "keyword")[:20],
        matched=bool(matched),
        fallback=bool(fallback),
        duration_ms=max(0, int(duration_ms)) if duration_ms is not None else None,
        metadata_json=metadata,
    )
    db.add(interaction)
    # 先分配 interaction_id，再为 fallback 建立同事务的待复核用例。
    db.flush()
    if interaction.fallback:
        from app.services.rag_evaluation_service import create_case_from_interaction

        create_case_from_interaction(db, interaction)
    return interaction


__all__ = ["record_rag_interaction"]
