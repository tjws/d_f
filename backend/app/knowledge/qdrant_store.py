"""Qdrant 连接和 Collection 初始化。

本模块只管理向量库连接与集合结构，不负责生成 Embedding，也不直接处理客户数据。
"""

from __future__ import annotations

import os

from qdrant_client import QdrantClient
from qdrant_client.http import models


DEFAULT_COLLECTION_NAME = "k12_knowledge"
DEFAULT_VECTOR_SIZE = 1024


def _collection_name() -> str:
    return os.getenv("QDRANT_COLLECTION", DEFAULT_COLLECTION_NAME).strip() or DEFAULT_COLLECTION_NAME


def _vector_size() -> int:
    raw_size = os.getenv("QDRANT_VECTOR_SIZE", str(DEFAULT_VECTOR_SIZE))
    try:
        size = int(raw_size)
    except ValueError:
        return DEFAULT_VECTOR_SIZE
    return size if size > 0 else DEFAULT_VECTOR_SIZE


def get_qdrant_client() -> QdrantClient:
    """根据环境变量创建客户端；API Key 为空时使用本地无认证模式。"""
    api_key = os.getenv("QDRANT_API_KEY", "").strip() or None
    return QdrantClient(
        url=os.getenv("QDRANT_URL", "http://localhost:6333").strip(),
        api_key=api_key,
        timeout=float(os.getenv("QDRANT_TIMEOUT_SECONDS", "5")),
    )


def ensure_collection(client: QdrantClient | None = None) -> str:
    """幂等创建知识库集合，重复执行不会覆盖已有向量。"""
    qdrant = client or get_qdrant_client()
    name = _collection_name()
    if not qdrant.collection_exists(collection_name=name):
        qdrant.create_collection(
            collection_name=name,
            vectors_config=models.VectorParams(size=_vector_size(), distance=models.Distance.COSINE),
        )
    return name


def upsert_chunks(
    points: list[models.PointStruct],
    client: QdrantClient | None = None,
) -> None:
    """写入知识分片向量；point id 使用 chunk id，重复索引会覆盖同一分片。"""
    if not points:
        return
    qdrant = client or get_qdrant_client()
    collection_name = ensure_collection(qdrant)
    qdrant.upsert(collection_name=collection_name, points=points, wait=True)


def search_vectors(
    vector: list[float],
    limit: int = 5,
    query_filter: models.Filter | None = None,
    client: QdrantClient | None = None,
) -> list[models.ScoredPoint]:
    """查询向量并返回带 payload 的结果；连接失败由上层决定是否降级。"""
    if limit <= 0:
        return []
    qdrant = client or get_qdrant_client()
    collection_name = ensure_collection(qdrant)
    response = qdrant.query_points(
        collection_name=collection_name,
        query=vector,
        limit=limit,
        with_payload=True,
        query_filter=query_filter,
    )
    return list(response.points)


def delete_document_vectors(document_id: int, client: QdrantClient | None = None) -> None:
    """删除文档旧版本的派生向量，避免编辑后召回过期内容。"""
    qdrant = client or get_qdrant_client()
    collection_name = ensure_collection(qdrant)
    qdrant.delete(
        collection_name=collection_name,
        points_selector=models.FilterSelector(
            filter=models.Filter(
                must=[models.FieldCondition(key="document_id", match=models.MatchValue(value=document_id))]
            )
        ),
        wait=True,
    )
