import base64
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


_KEY_ENV_NAME = "APP_ENCRYPTION_KEY"
_NONCE_SIZE = 12
_KEY_SIZE = 32


def _get_key() -> bytes:
    """从环境变量读取 32 字节 AES-256 密钥。"""

    encoded_key = os.getenv(_KEY_ENV_NAME)
    if not encoded_key:
        raise RuntimeError(
            f"{_KEY_ENV_NAME} 未设置，不能执行敏感数据加密。"
        )

    try:
        key = base64.urlsafe_b64decode(encoded_key.encode("ascii"))
    except Exception as exc:
        raise RuntimeError(
            f"{_KEY_ENV_NAME} 不是有效的 Base64 密钥。"
        ) from exc

    if len(key) != _KEY_SIZE:
        raise RuntimeError(
            f"{_KEY_ENV_NAME} 解码后必须是 {_KEY_SIZE} 字节。"
        )

    return key


def encrypt_text(plain_text: str) -> str:
    """使用 AES-GCM 加密文本，返回可保存到数据库的 Base64 字符串。"""

    nonce = os.urandom(_NONCE_SIZE)
    ciphertext = AESGCM(_get_key()).encrypt(
        nonce,
        plain_text.encode("utf-8"),
        None,
    )

    # 将 nonce 和密文拼接，方便数据库只保存一个字符串。
    return base64.urlsafe_b64encode(nonce + ciphertext).decode("ascii")


def decrypt_text(encoded_ciphertext: str) -> str:
    """解密 encrypt_text 生成的字符串。"""

    payload = base64.urlsafe_b64decode(encoded_ciphertext.encode("ascii"))

    if len(payload) <= _NONCE_SIZE:
        raise ValueError("密文长度无效。")

    nonce = payload[:_NONCE_SIZE]
    ciphertext = payload[_NONCE_SIZE:]

    plaintext = AESGCM(_get_key()).decrypt(
        nonce,
        ciphertext,
        None,
    )

    return plaintext.decode("utf-8")
