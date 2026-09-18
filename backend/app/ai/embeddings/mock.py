"""用于开发和测试的确定性向量，不代表真实语义质量。"""

from __future__ import annotations

import hashlib
import math


class MockEmbeddingProvider:
    model_name = "mock-hash-embedding"

    def __init__(self, dimension: int = 1024) -> None:
        self.dimension = dimension

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for text in texts:
            values: list[float] = []
            for index in range(self.dimension):
                digest = hashlib.sha256(f"{text}\0{index}".encode("utf-8")).digest()
                values.append((int.from_bytes(digest[:4], "big") / 2**32) * 2 - 1)
            norm = math.sqrt(sum(value * value for value in values)) or 1.0
            vectors.append([value / norm for value in values])
        return vectors

