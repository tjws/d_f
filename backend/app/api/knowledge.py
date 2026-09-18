from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, require_roles
from app.db.session import get_db
from app.knowledge.policy import retrieve_knowledge
from app.knowledge.evaluation import evaluate_knowledge
from app.models.user import User
from app.schemas.knowledge import KnowledgeDocumentCreate, KnowledgeDocumentRead, KnowledgeDocumentUpdate, KnowledgeSearchRead
from app.services.knowledge_service import create_document, list_documents, to_document_read, update_document
from app.services.knowledge_index_service import reindex_all_published
from app.ai.embeddings.factory import get_embedding_provider
from app.schemas.rag_evaluation import RAGEvaluationCaseRead, RAGEvaluationCaseReview
from app.services.rag_evaluation_service import build_evaluation_report, list_cases, review_case

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.get("/search", response_model=KnowledgeSearchRead)
def search_local_knowledge(
    q: str = Query(min_length=1, max_length=200),
    limit: int = Query(default=5, ge=1, le=10),
    use_vector: bool | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """供人工查看本地销售资料；不会把客户敏感信息写入知识库。"""
    result = retrieve_knowledge(
        q,
        limit=limit,
        db=db,
        # 允许验收脚本显式关闭向量检索，避免非必要的 Embedding 成本。
        use_vector=use_vector,
        consultant_name=current_user.full_name or current_user.username,
    )
    return {
        "query": result.query,
        "matched": result.matched,
        "retrieval_mode": result.retrieval_mode,
        "threshold": result.threshold,
        "fallback_message": result.fallback_message,
        "items": [
            {
                "document_id": item.document_id,
                "chunk_id": item.chunk_id,
                "title": item.title,
                "snippet": item.content[:500],
                "score": item.score,
            }
            for item in result.hits
        ],
    }


@router.get("/admin", response_model=list[KnowledgeDocumentRead])
def get_knowledge_documents(current_user: User = Depends(require_roles("admin", "manager")), db: Session = Depends(get_db)):
    return [to_document_read(item) for item in list_documents(db)]


@router.get("/admin/evaluation")
def evaluate_local_knowledge(limit: int = Query(default=3, ge=1, le=5), current_user: User = Depends(require_roles("admin", "manager")), db: Session = Depends(get_db)):
    """运行固定问题集评测；只读检索，不调用回复生成模型。"""
    del current_user
    return evaluate_knowledge(db=db, limit=limit)


@router.get("/admin/evaluation-cases", response_model=list[RAGEvaluationCaseRead])
def get_rag_evaluation_cases(
    status_filter: str | None = Query(default=None, alias="status", pattern="^(open|reviewed|ignored)$"),
    limit: int = Query(default=50, ge=1, le=200),
    current_user: User = Depends(require_roles("admin", "manager")),
    db: Session = Depends(get_db),
):
    del current_user
    return list_cases(db, status_filter, limit)


@router.get("/admin/evaluation-report")
def get_rag_evaluation_report(
    limit: int = Query(default=3, ge=1, le=5),
    current_user: User = Depends(require_roles("admin", "manager")),
    db: Session = Depends(get_db),
):
    del current_user
    return build_evaluation_report(db, limit)


@router.patch("/admin/evaluation-cases/{case_id}", response_model=RAGEvaluationCaseRead)
def patch_rag_evaluation_case(
    case_id: int,
    payload: RAGEvaluationCaseReview,
    current_user: User = Depends(require_roles("admin", "manager")),
    db: Session = Depends(get_db),
):
    return review_case(db, case_id, current_user, payload)


@router.post("/admin", response_model=KnowledgeDocumentRead, status_code=status.HTTP_201_CREATED)
def post_knowledge_document(payload: KnowledgeDocumentCreate, current_user: User = Depends(require_roles("admin", "manager")), db: Session = Depends(get_db)):
    return to_document_read(create_document(db, current_user, payload))


@router.patch("/admin/{document_id}", response_model=KnowledgeDocumentRead)
def patch_knowledge_document(document_id: int, payload: KnowledgeDocumentUpdate, current_user: User = Depends(require_roles("admin", "manager")), db: Session = Depends(get_db)):
    return to_document_read(update_document(db, document_id, current_user, payload))


@router.post("/admin/reindex")
def reindex_knowledge_vectors(current_user: User = Depends(require_roles("admin", "manager")), db: Session = Depends(get_db)):
    """显式触发已发布知识向量化；不在普通页面加载时消耗 Embedding 配额。"""
    try:
        del db
        count = reindex_all_published(force=True)
        provider = get_embedding_provider()
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="知识库向量索引暂不可用") from exc
    return {"indexed": count, "provider": provider.model_name}
