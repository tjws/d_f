import os

from app.integrations.transcription.base import TranscriptionProvider
from app.integrations.transcription.mock import MockTranscriptionProvider


def get_transcription_provider() -> TranscriptionProvider:
    """保留外部 ASR 扩展点，但未知/空配置均安全回落到 Mock。"""

    provider = os.getenv("VOICE_TRANSCRIPTION_PROVIDER", "mock").strip().lower()
    if provider in {"", "mock"}:
        return MockTranscriptionProvider()
    raise RuntimeError(f"不支持的语音转写 provider: {provider}")

