from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


RAGEvaluationCaseStatus = Literal["open", "reviewed", "ignored"]


class RAGEvaluationCaseReview(BaseModel):
    status: RAGEvaluationCaseStatus
    expected_document_ids: list[str] = Field(default_factory=list, max_length=20)
    review_note: str | None = Field(default=None, max_length=500)


class RAGEvaluationCaseRead(BaseModel):
    id: int
    interaction_id: int | None
    customer_id: int | None
    run_id: int | None
    actor_user_id: int | None
    source_type: str
    source_id: str
    query_excerpt: str | None
    retrieval_mode: str | None
    fallback: bool
    expected_document_ids: list[str] | None
    retrieved_document_ids: list[str] | None
    status: RAGEvaluationCaseStatus
    review_note: str | None
    reviewed_by: int | None
    reviewed_at: datetime | None
    created_at: datetime
    updated_at: datetime

