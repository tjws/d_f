"""客户流失批量评分 Worker。"""

import dramatiq

from app.services.churn_model_governance_service import execute_registered_churn_scoring
from app.workers.broker import broker  # noqa: F401


@dramatiq.actor(queue_name="churn_scoring", max_retries=1, time_limit=300_000)
def execute_churn_scoring_task(
    source_filename: str,
    model_version_id: int,
    source_system: str = "csv",
    observation_at: str | None = None,
    trigger_source: str = "scheduler",
) -> None:
    execute_registered_churn_scoring(
        source_filename,
        model_version_id,
        source_system,
        observation_at,
        trigger_source,
    )
