"""阿里云百炼文本向量 Provider；只有显式配置时才会调用。"""

from __future__ import annotations

import os
from typing import Any

from openai import OpenAI


class BailianEmbeddingError(ValueError):
    """百炼 Embedding 配置或调用失败。"""


class BailianEmbeddingProvider:
    model_name = "text-embedding-v4"

    def __init__(self, client: Any | None = None) -> None:
        self._client = client
        self.model_name = os.getenv("BAILIAN_EMBEDDING_MODEL", self.model_name).strip() or self.model_name
        self.dimension = int(os.getenv("BAILIAN_EMBEDDING_DIMENSION", "1024"))

    def _client_or_raise(self) -> Any:
        if self._client is not None:
            return self._client
        api_key = os.getenv("DASHSCOPE_API_KEY")
        if not api_key:
            raise BailianEmbeddingError("DASHSCOPE_API_KEY is required for Bailian embeddings")
        self._client = OpenAI(
            api_key=api_key,
            base_url=os.getenv("BAILIAN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
            timeout=20.0,
            max_retries=0,
        )
        return self._client

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        try:
            response = self._client_or_raise().embeddings.create(
                model=self.model_name,
                input=texts,
                dimensions=self.dimension,
            )
            rows = sorted(response.data, key=lambda item: item.index)
            vectors = [list(map(float, row.embedding)) for row in rows]
        except BailianEmbeddingError:
            raise
        except Exception as exc:
            raise BailianEmbeddingError("Bailian embedding request failed") from exc
        if len(vectors) != len(texts) or any(len(vector) != self.dimension for vector in vectors):
            raise BailianEmbeddingError("Bailian embedding dimension mismatch")
        return vectors

