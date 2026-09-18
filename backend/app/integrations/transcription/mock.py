class MockTranscriptionProvider:
    """不上传文件、不调用外部模型的确定性语音转写替身。"""

    def transcribe(self, media_object_key: str) -> str:
        if media_object_key.startswith("mock-voice:"):
            transcript = media_object_key.removeprefix("mock-voice:").strip()
            if transcript:
                return transcript
        return f"Mock voice transcript for {media_object_key}"

