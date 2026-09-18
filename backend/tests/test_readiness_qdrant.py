from fastapi.testclient import TestClient

import app.main as main_module
from app.main import app


class _FakeRedis:
    def ping(self):
        return True

    def close(self):
        return None


class _FakeQdrant:
    def get_collections(self):
        return {"collections": []}


def test_readiness_checks_qdrant_when_vector_search_is_enabled(monkeypatch):
    monkeypatch.setenv("RAG_VECTOR_ENABLED", "1")
    monkeypatch.setattr(main_module.redis.Redis, "from_url", lambda *args, **kwargs: _FakeRedis())
    monkeypatch.setattr(main_module, "get_qdrant_client", lambda: _FakeQdrant())

    response = TestClient(app).get("/health/ready")

    assert response.status_code == 200
    assert response.json()["checks"]["qdrant"] == "ok"
