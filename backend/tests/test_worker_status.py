import json

from app.services import system_status_service as status_service
from app.workers.heartbeat import WorkerHeartbeatMiddleware


class _HeartbeatRedis:
    def __init__(self, payload: bytes | None = None):
        self.payload = payload
        self.writes: list[tuple[str, int, str]] = []
        self.deleted: list[str] = []

    def setex(self, key: str, ttl: int, value: str):
        self.writes.append((key, ttl, value))

    def get(self, key: str):
        return self.payload

    def delete(self, key: str):
        self.deleted.append(key)

    def close(self):
        return None


def test_worker_heartbeat_uses_ttl_and_cleans_up():
    client = _HeartbeatRedis()
    middleware = WorkerHeartbeatMiddleware(
        redis_factory=lambda *args, **kwargs: client,
        heartbeat_key="test:worker",
        interval_seconds=2,
        ttl_seconds=8,
    )
    middleware._write_heartbeat()
    middleware._clear_heartbeat()
    assert client.writes[0][0:2] == ("test:worker", 8)
    assert json.loads(client.writes[0][2])["worker_id"] == middleware.worker_id
    assert client.deleted == ["test:worker"]


def test_worker_status_reports_online_and_queue_depths(monkeypatch):
    payload = json.dumps({"worker_id": "worker-1", "updated_at": "2026-09-16T04:00:00+00:00"}).encode()
    client = _HeartbeatRedis(payload)
    monkeypatch.setenv("AI_WORKFLOW_EXECUTION_MODE", "queue")
    monkeypatch.setenv("KNOWLEDGE_INDEX_EXECUTION_MODE", "manual")
    monkeypatch.setattr(status_service.redis.Redis, "from_url", lambda *args, **kwargs: client)
    monkeypatch.setattr(status_service.worker_broker, "do_qsize", lambda queue: 3 if queue == "ai_workflow" else 1)

    result = status_service.get_worker_status()
    assert result["required"] is True
    assert result["status"] == "online"
    assert result["worker_id"] == "worker-1"
    assert result["queue_depths"] == {"ai_workflow": 3, "knowledge_index": 1}
