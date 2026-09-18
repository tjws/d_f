from datetime import datetime
from typing import Any

from pydantic import BaseModel


class AIDashboardRead(BaseModel):
    start: datetime
    end: datetime
    suggestions_total: int
    feedback_total: int
    accepted: int
    edited: int
    rejected: int
    adoption_rate: float
    by_suggestion_type: dict[str, dict[str, int]]
    workflow: dict[str, int]
    bailian_calls: int
    bailian_failures: int
    rag_queries_total: int
    rag_fallbacks: int
    rag_fallback_rate: float
    agent_feedback_total: int
    agent_feedback_by_action: dict[str, int]
    agent_reasoning_total: int
    agent_reasoning_failures: int
    agent_reasoning_failure_rate: float
    avg_task_duration_ms: int
