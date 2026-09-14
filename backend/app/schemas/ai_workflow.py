from typing import Literal

from pydantic import BaseModel


class AIWorkflowRunRead(BaseModel):
    """一次 LangGraph 运行的结果；建议仍需人工确认。"""

    customer_id: int
    status: Literal["waiting_human", "failed"]
    suggestion_ids: list[int] = []
    error: str | None = None
