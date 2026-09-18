"""初始化 Qdrant 知识库 Collection，不生成或上传任何向量。"""

from app.knowledge.qdrant_store import ensure_collection, get_qdrant_client


def main() -> int:
    client = get_qdrant_client()
    collection_name = ensure_collection(client)
    info = client.get_collection(collection_name)
    print(f"qdrant_collection={collection_name} status={info.status} points={info.points_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

