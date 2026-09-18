"""Dramatiq Worker 的轻量心跳。Redis 中只保存短期运行状态，不保存业务数据。"""

from __future__ import annotations

from datetime import datetime, timezone
import json
import logging
import os
from threading import Event, Thread
from typing import Any, Callable
from uuid import uuid4

import redis
from dramatiq.middleware import Middleware


logger = logging.getLogger("k12.worker")


class WorkerHeartbeatMiddleware(Middleware):
    """让 Worker 在线状态可被管理后台读取；TTL 到期即视为离线。"""

    def __init__(
        self,
        *,
        redis_factory: Callable[..., Any] | None = None,
        heartbeat_key: str | None = None,
        interval_seconds: int = 10,
        ttl_seconds: int = 30,
    ) -> None:
        self.redis_factory = redis_factory
        self.heartbeat_key = heartbeat_key or os.getenv(
            "WORKER_HEARTBEAT_KEY", "k12_sales_assistant:worker:heartbeat"
        )
        self.interval_seconds = max(1, interval_seconds)
        self.ttl_seconds = max(self.interval_seconds + 1, ttl_seconds)
        self.worker_id = f"{os.getenv('HOSTNAME', 'local-worker')}:{os.getpid()}:{uuid4().hex[:8]}"
        self._stop_event = Event()
        self._thread: Thread | None = None

    def _client(self):
        factory = self.redis_factory or redis.Redis.from_url
        return factory(os.getenv("REDIS_URL", "redis://localhost:6380/0"))

    def _write_heartbeat(self) -> None:
        client = self._client()
        try:
            payload = json.dumps(
                {
                    "worker_id": self.worker_id,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            )
            client.setex(self.heartbeat_key, self.ttl_seconds, payload)
        finally:
            close = getattr(client, "close", None)
            if close is not None:
                close()

    def _clear_heartbeat(self) -> None:
        client = self._client()
        try:
            client.delete(self.heartbeat_key)
        finally:
            close = getattr(client, "close", None)
            if close is not None:
                close()

    def _run(self) -> None:
        while not self._stop_event.wait(self.interval_seconds):
            try:
                self._write_heartbeat()
            except Exception:
                # 心跳失败不能让 Worker 退出；管理后台会显示 offline/error。
                logger.warning("worker_heartbeat_failed", exc_info=True)

    def after_worker_boot(self, broker, worker) -> None:  # noqa: D401, ANN001
        del broker, worker
        self._stop_event.clear()
        self._write_heartbeat()
        self._thread = Thread(target=self._run, name="worker-heartbeat", daemon=True)
        self._thread.start()

    def before_worker_shutdown(self, broker, worker) -> None:  # noqa: D401, ANN001
        del broker, worker
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=2)
            self._thread = None
        try:
            self._clear_heartbeat()
        except Exception:
            logger.warning("worker_heartbeat_cleanup_failed", exc_info=True)
