"""将已发布知识分片索引到 Qdrant；默认使用 Mock Embedding。"""

from app.db.session import SessionLocal
from app.services.knowledge_embedding_service import index_published_knowledge


def main() -> int:
    with SessionLocal() as db:
        count = index_published_knowledge(db)
    print(f"indexed_knowledge_chunks={count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

