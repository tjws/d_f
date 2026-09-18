"""RAG 评测用例的创建、复核和报告服务。"""

from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.dao.rag_evaluation_case_dao import RAGEvaluationCaseDAO
from app.knowledge.evaluation import evaluate_knowledge
from app.models.ai_rag_interaction import AIRagInteraction
from app.models.ai_workflow_run import AIWorkflowRun
from app.models.rag_evaluation_case import RAGEvaluationCase
from app.models.user import User
from app.schemas.rag_evaluation import RAGEvaluationCaseReview
from app.services.audit_log_service import append_audit_log


case_dao = RAGEvaluationCaseDAO()


def _list_ids(value: object) -> list[str] | None:
    if not isinstance(value, list):
        return None
    values = [str(item).strip()[:120] for item in value if str(item).strip()]
    return list(dict.fromkeys(values))[:50] or None


def _case_read(case: RAGEvaluationCase) -> dict[str, Any]:
    return {
        "id": case.id,
        "interaction_id": case.interaction_id,
        "customer_id": case.customer_id,
        "run_id": case.run_id,
        "actor_user_id": case.actor_user_id,
        "source_type": case.source_type,
        "source_id": case.source_id,
        "query_excerpt": case.query_excerpt,
        "retrieval_mode": case.retrieval_mode,
        "fallback": case.fallback,
        "expected_document_ids": case.expected_document_ids,
        "retrieved_document_ids": case.retrieved_document_ids,
        "status": case.status,
        "review_note": case.review_note,
        "reviewed_by": case.reviewed_by,
        "reviewed_at": case.reviewed_at,
        "created_at": case.created_at,
        "updated_at": case.updated_at,
    }


def create_case_from_interaction(db: Session, interaction: AIRagInteraction) -> RAGEvaluationCase | None:
    """fallback 时在同一事务中创建一条待复核用例，重复写入保持幂等。"""

    if not interaction.fallback:
        return None
    source_type, source_id = "rag_fallback", str(interaction.id)
    existing = case_dao.get_by_source(db, source_type, source_id)
    if existing is not None:
        return existing
    metadata = interaction.metadata_json if isinstance(interaction.metadata_json, dict) else {}
    case = RAGEvaluationCase(
        interaction_id=interaction.id,
        customer_id=interaction.customer_id,
        run_id=interaction.run_id,
        actor_user_id=interaction.actor_user_id,
        source_type=source_type,
        source_id=source_id,
        query_excerpt=interaction.query_excerpt,
        retrieval_mode=interaction.retrieval_mode,
        fallback=True,
        retrieved_document_ids=_list_ids(metadata.get("document_ids")),
        status="open",
    )
    case_dao.add(db, case)
    return case


def create_case_from_agent_feedback(
    db: Session, run: AIWorkflowRun, actor: User
) -> RAGEvaluationCase:
    """Agent 反馈也建立可追踪用例；没有 RAG 命中时允许查询摘要为空。"""

    source_type, source_id = "agent_feedback", str(run.id)
    existing = case_dao.get_by_source(db, source_type, source_id)
    if existing is not None:
        return existing
    interaction = db.scalar(
        select(AIRagInteraction)
        .where(AIRagInteraction.run_id == run.id)
        .order_by(AIRagInteraction.created_at.desc())
    )
    case = RAGEvaluationCase(
        interaction_id=interaction.id if interaction else None,
        customer_id=run.customer_id,
        run_id=run.id,
        actor_user_id=actor.id,
        source_type=source_type,
        source_id=source_id,
        query_excerpt=interaction.query_excerpt if interaction else None,
        retrieval_mode=interaction.retrieval_mode if interaction else None,
        fallback=bool(interaction and interaction.fallback),
        retrieved_document_ids=_list_ids(
            (interaction.metadata_json or {}).get("document_ids")
            if interaction and isinstance(interaction.metadata_json, dict)
            else None
        ),
        status="open",
    )
    case_dao.add(db, case)
    return case


def list_cases(db: Session, status_filter: str | None, limit: int) -> list[dict[str, Any]]:
    return [_case_read(case) for case in case_dao.list(db, status_filter, max(1, min(limit, 200)))]


def review_case(
    db: Session, case_id: int, actor: User, payload: RAGEvaluationCaseReview
) -> dict[str, Any]:
    case = case_dao.get_by_id(db, case_id)
    if case is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="RAG 评测用例不存在")
    if payload.status == "open":
        case.reviewed_by = None
        case.reviewed_at = None
    else:
        case.reviewed_by = actor.id
        case.reviewed_at = datetime.now(timezone.utc)
    case.status = payload.status
    case.expected_document_ids = _list_ids(payload.expected_document_ids)
    case.review_note = (payload.review_note or "").strip()[:500] or None
    append_audit_log(
        db,
        actor,
        "rag.evaluation_case_reviewed",
        "rag_evaluation_case",
        str(case.id),
        {"status": case.status, "expected_document_count": len(case.expected_document_ids or [])},
    )
    db.commit()
    db.refresh(case)
    return _case_read(case)


def build_evaluation_report(db: Session, limit: int = 3) -> dict[str, Any]:
    """返回固定评测结果和人工复核队列；默认不调用生成模型。"""

    safe_limit = max(1, min(limit, 5))
    cases = case_dao.list(db, None, 200)
    queue = {
        "total": len(cases),
        "open": sum(case.status == "open" for case in cases),
        "reviewed": sum(case.status == "reviewed" for case in cases),
        "ignored": sum(case.status == "ignored" for case in cases),
        "fallback": sum(case.fallback for case in cases),
    }
    return {
        "generated_at": datetime.now(timezone.utc),
        "fixed_evaluation": evaluate_knowledge(db=db, limit=safe_limit),
        "queue": queue,
        "cases": [_case_read(case) for case in cases[:50]],
    }


__all__ = [
    "build_evaluation_report",
    "create_case_from_agent_feedback",
    "create_case_from_interaction",
    "list_cases",
    "review_case",
]

