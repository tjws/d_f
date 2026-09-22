"""轻量定时投递器；实际评分由 Dramatiq Worker 执行。"""

from datetime import datetime, timezone
import os
from pathlib import Path
import time

from app.dao.churn_model_version_dao import ChurnModelVersionDAO
from app.db.session import SessionLocal
from app.services.churn_model_governance_service import churn_import_directory
from app.workers.churn_tasks import execute_churn_scoring_task


def enqueue_latest_import() -> str | None:
    import_dir = churn_import_directory()
    files = sorted(import_dir.glob("*.csv"), key=lambda path: path.stat().st_mtime, reverse=True)
    if not files:
        return None
    with SessionLocal() as db:
        model = ChurnModelVersionDAO().get_approved(db)
        if model is None:
            return None
        message = execute_churn_scoring_task.send(
            files[0].name,
            model.id,
            os.getenv("CHURN_SOURCE_SYSTEM", "csv"),
            datetime.now(timezone.utc).isoformat(),
            "scheduler",
        )
        return message.message_id


def main() -> None:
    if os.getenv("CHURN_SCORING_SCHEDULE_ENABLED", "0") != "1":
        print("CHURN_SCORING_SCHEDULE_ENABLED=0，定时评分未启用")
        return
    interval = max(300, int(os.getenv("CHURN_SCORING_INTERVAL_SECONDS", "86400")))
    churn_import_directory().mkdir(parents=True, exist_ok=True)
    while True:
        message_id = enqueue_latest_import()
        print(f"churn scheduler queued={message_id or 'none'}", flush=True)
        time.sleep(interval)


if __name__ == "__main__":
    main()
