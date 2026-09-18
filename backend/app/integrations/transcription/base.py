from typing import Protocol


class TranscriptionProvider(Protocol):
    def transcribe(self, media_object_key: str) -> str:
        """根据媒体对象引用返回转写文本。"""

