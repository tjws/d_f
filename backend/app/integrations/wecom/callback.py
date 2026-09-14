import hashlib
import hmac
from collections.abc import Callable
from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError

from app.dao.integration_event_dao import IntegrationEventDAO
from app.models.integration_event import IntegrationEvent


def build_mock_signature(
    token: str,
    timestamp: str,
    nonce: str,
    body: str,
) -> str:
    """生成 Mock 回调签名；真实企业微信适配器以后单独实现协议。"""

    message = f"{timestamp}:{nonce}:{body}".encode()

    return hmac.new(
        token.encode(),
        message,
        hashlib.sha256,
    ).hexdigest()


def verify_mock_signature(
    token: str,
    timestamp: str,
    nonce: str,
    body: str,
    signature: str,
) -> bool:
    """安全比较 Mock 回调签名，避免普通字符串比较的时序问题。"""

    expected = build_mock_signature(
        token,
        timestamp,
        nonce,
        body,
    )

    return hmac.compare_digest(expected, signature)


class MockCallbackProcessor:
    """本地模拟回调处理器。"""

    def __init__(self):
        self._processed_event_ids: set[str] = set()

    def process(
        self,
        event_id: str,
        handler: Callable[[], None],
    ) -> str:
        """处理事件；成功后记录，失败时允许重试。"""

        if event_id in self._processed_event_ids:
            return "duplicate"

        try:
            handler()
        except Exception:
            return "retry"

        self._processed_event_ids.add(event_id)
        return "processed"


class DatabaseCallbackProcessor:
    """使用 integration_events 表持久化处理状态。"""

    def __init__(self, session_factory):
        self.session_factory = session_factory
        self.event_dao = IntegrationEventDAO()

    def process(
        self,
        provider: str,
        external_event_id: str,
        event_type: str,
        handler: Callable[[], None],
        payload_encrypted: str | None = None,
    ) -> str:
        """登记、处理并更新外部事件状态。"""

        with self.session_factory() as db:
            event = self.event_dao.get(db, provider, external_event_id)

            if event is None:
                event = IntegrationEvent(
                    provider=provider,
                    external_event_id=external_event_id,
                    event_type=event_type,
                    payload_encrypted=payload_encrypted,
                    status="received",
                )
                self.event_dao.add(db, event)

                try:
                    db.commit()
                except IntegrityError:
                    # 并发请求可能已经登记了相同事件。
                    db.rollback()
                    event = self.event_dao.get(db, provider, external_event_id)

            if event is None:
                raise RuntimeError("事件登记失败")

            if event.status == "processed":
                return "duplicate"

            event_id = event.id
            claim_result = self.event_dao.claim(db, event_id)
            db.commit()

            # 已由其他请求领取的 processing 事件不重复执行。
            if claim_result != 1:
                return "in_progress"

        try:
            handler()
        except Exception as exc:
            with self.session_factory() as db:
                self.event_dao.mark_failed(db, event_id, str(exc))
                db.commit()

            return "retry"

        with self.session_factory() as db:
            self.event_dao.mark_processed(db, event_id, datetime.now(timezone.utc))
            db.commit()

        return "processed"
