from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.integration_event import IntegrationEvent


class IntegrationEventDAO:
    """外部事件的幂等状态读写；状态机的判断留在回调处理服务。"""

    def get(self, db: Session, provider: str, external_event_id: str) -> IntegrationEvent | None:
        return db.scalar(select(IntegrationEvent).where(IntegrationEvent.provider == provider, IntegrationEvent.external_event_id == external_event_id))

    def add(self, db: Session, event: IntegrationEvent) -> None:
        db.add(event)

    def claim(self, db: Session, event_id: int) -> int:
        result = db.execute(update(IntegrationEvent).where(IntegrationEvent.id == event_id, IntegrationEvent.status.in_(("received", "failed"))).values(status="processing", retry_count=IntegrationEvent.retry_count + 1))
        return result.rowcount

    def mark_failed(self, db: Session, event_id: int, error: str) -> None:
        db.execute(update(IntegrationEvent).where(IntegrationEvent.id == event_id).values(status="failed", last_error=error))

    def mark_processed(self, db: Session, event_id: int, processed_at: datetime) -> None:
        db.execute(update(IntegrationEvent).where(IntegrationEvent.id == event_id).values(status="processed", processed_at=processed_at, last_error=None))
