import base64

import pytest
from cryptography.exceptions import InvalidTag

from app.core.crypto import decrypt_text, encrypt_text


def _encoded_key(seed: bytes) -> str:
    return base64.urlsafe_b64encode(seed).decode("ascii")


def test_encrypt_and_decrypt_round_trip_uses_random_nonce(monkeypatch):
    """同一明文每次使用不同 nonce，但都可以正确解密。"""

    monkeypatch.setenv("APP_ENCRYPTION_KEY", _encoded_key(b"a" * 32))

    first = encrypt_text("小明-数学")
    second = encrypt_text("小明-数学")

    assert first != second
    assert decrypt_text(first) == "小明-数学"
    assert decrypt_text(second) == "小明-数学"


def test_encrypt_requires_key(monkeypatch):
    monkeypatch.delenv("APP_ENCRYPTION_KEY", raising=False)

    with pytest.raises(RuntimeError, match="APP_ENCRYPTION_KEY 未设置"):
        encrypt_text("敏感资料")


def test_encrypt_rejects_wrong_key_length(monkeypatch):
    monkeypatch.setenv("APP_ENCRYPTION_KEY", _encoded_key(b"short"))

    with pytest.raises(RuntimeError, match="必须是 32 字节"):
        encrypt_text("敏感资料")


def test_decrypt_rejects_wrong_key(monkeypatch):
    monkeypatch.setenv("APP_ENCRYPTION_KEY", _encoded_key(b"a" * 32))
    ciphertext = encrypt_text("敏感资料")

    monkeypatch.setenv("APP_ENCRYPTION_KEY", _encoded_key(b"b" * 32))

    with pytest.raises(InvalidTag):
        decrypt_text(ciphertext)


def test_decrypt_rejects_tampered_ciphertext(monkeypatch):
    monkeypatch.setenv("APP_ENCRYPTION_KEY", _encoded_key(b"a" * 32))
    ciphertext = encrypt_text("敏感资料")

    payload = bytearray(base64.urlsafe_b64decode(ciphertext))
    payload[-1] ^= 1
    tampered = base64.urlsafe_b64encode(payload).decode("ascii")

    with pytest.raises(InvalidTag):
        decrypt_text(tampered)


def test_decrypt_rejects_too_short_ciphertext(monkeypatch):
    monkeypatch.setenv("APP_ENCRYPTION_KEY", _encoded_key(b"a" * 32))

    with pytest.raises(ValueError, match="密文长度无效"):
        decrypt_text(base64.urlsafe_b64encode(b"too-short").decode("ascii"))
