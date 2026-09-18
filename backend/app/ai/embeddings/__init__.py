"""Embedding Provider：Mock 默认，百炼按环境变量显式启用。"""

from app.ai.embeddings.factory import get_embedding_provider

__all__ = ["get_embedding_provider"]

