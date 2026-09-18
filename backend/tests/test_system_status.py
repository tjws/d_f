import uuid

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.session import SessionLocal
from app.main import app
from app.models.user import User


client = TestClient(app)


class _FakeRedis:
    def ping(self):
        return True

    def close(self):
        return None


class _FakeQdrant:
    def get_collections(self):
        return {"collections": []}


def _login_as(role: str) -> dict[str, str]:
    username = f"system_status_{uuid.uuid4().hex[:8]}"
    password = "Test123!"
    registered = client.post("/auth/register", json={"username": username, "password": password})
    assert registered.status_code == 201
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.username == username))
        assert user is not None
        user.role = role
        db.commit()
    login = client.post("/auth/token", data={"username": username, "password": password})
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def test_system_status_is_role_protected_and_does_not_expose_bailian_key(monkeypatch):
    import app.services.system_status_service as status_service

    monkeypatch.setenv("RAG_VECTOR_ENABLED", "1")
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)
    monkeypatch.setattr(status_service.redis.Redis, "from_url", lambda *args, **kwargs: _FakeRedis())
    monkeypatch.setattr(status_service, "default_qdrant_factory", lambda: _FakeQdrant())

    headers = _login_as("admin")
    response = client.get("/admin/system-status", headers=headers)
    assert response.status_code == 200
    payload = response.json()
    assert payload["ready"] is True
    assert payload["dependencies"]["qdrant"]["status"] == "ok"
    assert payload["ai"]["bailian_api_key_configured"] is False
    assert "DASHSCOPE_API_KEY" not in response.text

    sales_headers = _login_as("sales")
    denied = client.get("/admin/system-status", headers=sales_headers)
    assert denied.status_code == 403
