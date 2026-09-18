"""固定问题集的 RAG 召回评测；只读检索，不调用生成模型。"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.knowledge.retriever import KnowledgeDocument, search_knowledge


@dataclass(frozen=True)
class EvaluationCase:
    query: str
    expected_document_ids: tuple[str, ...]


CASES: tuple[EvaluationCase, ...] = (
    EvaluationCase("试听课需要多长时间", ("02_math_trial", "trial_process_demo")),
    EvaluationCase("课程价格应该怎么沟通", ("03_pricing_faq",)),
    EvaluationCase("家长担心没有时间", ("04_objection_handling",)),
    EvaluationCase("首次咨询后什么时候跟进", ("05_followup_playbook", "followup_policy_demo")),
    EvaluationCase("手机号和学校信息能给 AI 吗", ("06_privacy_safety",)),
    EvaluationCase("孩子成绩不稳定怎么沟通", ("07_parent_conversation",)),
    EvaluationCase("英语词汇阅读听力怎么学", ("08_subject_methods", "subject_methods_demo")),
    EvaluationCase("退费和转课怎么处理", ("09_refund_and_service",)),
    EvaluationCase("发送前需要检查什么", ("10_quality_checklist",)),
)


def _hit_payload(results: list[KnowledgeDocument], expected_ids: tuple[str, ...], limit: int) -> dict[str, object]:
    hits = [
        {
            "document_id": item.document_id,
            "chunk_id": item.chunk_id,
            "title": item.title,
            "score": item.score,
            "snippet": item.content[:240],
        }
        for item in results
    ]
    matched = next((item.document_id for item in results if item.document_id in expected_ids), None)
    rank = next((index + 1 for index, item in enumerate(results) if item.document_id in expected_ids), None)
    return {"expected_document_ids": list(expected_ids), "matched_document_id": matched, "hit": rank is not None, "rank": rank, "reciprocal_rank": 1 / rank if rank else 0.0, "hits": hits[:limit]}


def evaluate_knowledge(db: Session | None = None, limit: int = 3) -> dict[str, object]:
    """同时评测关键词和向量模式，结果可直接用于管理端或命令行展示。"""
    safe_limit = max(1, min(limit, 5))
    modes: dict[str, list[dict[str, object]]] = {"keyword": [], "vector": []}
    for case in CASES:
        modes["keyword"].append({"query": case.query, **_hit_payload(search_knowledge(case.query, safe_limit, db=db, use_vector=False), case.expected_document_ids, safe_limit)})
        modes["vector"].append({"query": case.query, **_hit_payload(search_knowledge(case.query, safe_limit, db=db, use_vector=True), case.expected_document_ids, safe_limit)})

    summary: dict[str, dict[str, float]] = {}
    for mode, rows in modes.items():
        summary[mode] = {
            "hit_at_k": sum(bool(row["hit"]) for row in rows) / len(rows),
            "mean_reciprocal_rank": sum(float(row["reciprocal_rank"]) for row in rows) / len(rows),
        }
    return {"k": safe_limit, "case_count": len(CASES), "summary": summary, "cases": modes}
