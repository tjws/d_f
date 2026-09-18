from __future__ import annotations

import os

from app.ai.embeddings.bailian import BailianEmbeddingProvider
from app.ai.embeddings.mock import MockEmbeddingProvider
from app.ai.providers.base import EmbeddingProvider


def get_embedding_provider() -> EmbeddingProvider:
    """未配置时使用 Mock，避免索引或检索意外产生百炼费用。"""
    provider_name = os.getenv("RAG_EMBEDDING_PROVIDER", "mock").strip().lower()
    if provider_name == "mock":
        return MockEmbeddingProvider(int(os.getenv("QDRANT_VECTOR_SIZE", "1024")))
    if provider_name == "bailian":
        return BailianEmbeddingProvider()
    raise ValueError(f"unsupported RAG_EMBEDDING_PROVIDER: {provider_name}")

