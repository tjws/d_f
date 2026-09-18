from qdrant_client.http import models

from app.knowledge.qdrant_store import ensure_collection


class FakeQdrantClient:
    def __init__(self):
        self.collections: set[str] = set()
        self.created: list[tuple[str, models.VectorParams]] = []

    def collection_exists(self, *, collection_name: str) -> bool:
        return collection_name in self.collections

    def create_collection(self, *, collection_name: str, vectors_config: models.VectorParams) -> None:
        self.collections.add(collection_name)
        self.created.append((collection_name, vectors_config))


def test_ensure_collection_is_idempotent(monkeypatch):
    monkeypatch.setenv("QDRANT_COLLECTION", "test_knowledge")
    monkeypatch.setenv("QDRANT_VECTOR_SIZE", "1024")
    client = FakeQdrantClient()

    assert ensure_collection(client) == "test_knowledge"
    assert ensure_collection(client) == "test_knowledge"
    assert len(client.created) == 1
    assert client.created[0][1].size == 1024

