"""知识库向量索引 Worker 任务。"""

import dramatiq

from app.services.knowledge_index_service import index_one_document
from app.workers.broker import broker  # noqa: F401


@dramatiq.actor(queue_name="knowledge_index", max_retries=2, time_limit=120_000)
def index_knowledge_document_task(document_id: int) -> None:
    index_one_document(document_id)
