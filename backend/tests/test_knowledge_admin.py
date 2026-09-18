from sqlalchemy import delete, select
from fastapi.testclient import TestClient

from app.db.session import SessionLocal
from app.main import app
from app.models.knowledge_chunk import KnowledgeChunk
from app.models.knowledge_document import KnowledgeDocument
from app.models.user import User
from app.knowledge.policy import KnowledgeRetrievalResult


client = TestClient(app)


def setup_function():
    with SessionLocal() as db:
        db.execute(delete(KnowledgeChunk))
        db.execute(delete(KnowledgeDocument))
        db.execute(delete(User))
        db.commit()


def _admin_headers() -> dict[str, str]:
    created = client.post("/auth/register", json={"username": "kb_admin", "password": "Test123!"})
    assert created.status_code == 201
    with SessionLocal() as db:
        admin = db.scalar(select(User).where(User.username == "kb_admin"))
        admin.role = "admin"
        db.commit()
    token = client.post("/auth/token", data={"username": "kb_admin", "password": "Test123!"}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_knowledge_draft_publish_and_search():
    headers = _admin_headers()
    created = client.post(
        "/knowledge/admin",
        headers=headers,
        json={"slug": "kb_trial_test", "title": "测试试听资料", "category": "试听", "content": "试听先确认目标，再进行讲解和练习。"},
    )
    assert created.status_code == 201
    document_id = created.json()["id"]
    assert created.json()["status"] == "draft"
    draft_hits = client.get("/knowledge/search", params={"q": "试听"}, headers=headers).json()["items"]
    assert all(item["document_id"] != "kb_trial_test" for item in draft_hits)

    published = client.patch(f"/knowledge/admin/{document_id}", headers=headers, json={"status": "published"})
    assert published.status_code == 200
    hits = client.get("/knowledge/search", params={"q": "试听"}, headers=headers)
    assert hits.status_code == 200
    assert any(item["document_id"] == "kb_trial_test" and item["chunk_id"] for item in hits.json()["items"])

    disabled = client.patch(f"/knowledge/admin/{document_id}", headers=headers, json={"status": "disabled"})
    assert disabled.status_code == 200
    assert all(item["document_id"] != "kb_trial_test" for item in client.get("/knowledge/search", params={"q": "试听"}, headers=headers).json()["items"])


def test_sales_cannot_manage_knowledge():
    headers = _admin_headers()
    user = client.post("/auth/register", json={"username": "kb_sales", "password": "Test123!"})
    assert user.status_code == 201
    with SessionLocal() as db:
        sales = db.scalar(select(User).where(User.username == "kb_sales"))
        sales.role = "sales"
        db.commit()
    token = client.post("/auth/token", data={"username": "kb_sales", "password": "Test123!"}).json()["access_token"]
    response = client.get("/knowledge/admin", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403


def test_knowledge_search_can_disable_vector_retrieval(monkeypatch):
    headers = _admin_headers()
    observed: dict[str, object] = {}

    def fake_retrieve(query: str, **kwargs):
        observed.update(kwargs)
        return KnowledgeRetrievalResult(
            hits=(),
            matched=False,
            retrieval_mode="keyword",
            threshold=2.0,
            fallback_message="no match",
            query=query,
        )

    monkeypatch.setattr("app.api.knowledge.retrieve_knowledge", fake_retrieve)
    response = client.get("/knowledge/search", params={"q": "试听", "use_vector": "false"}, headers=headers)

    assert response.status_code == 200
    assert observed["use_vector"] is False
