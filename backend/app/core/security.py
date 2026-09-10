import os
from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash
from fastapi.security import OAuth2PasswordBearer

# 使用 Argon2 进行密码哈希。
# 数据库中只保存哈希值，不保存用户明文密码。
password_hash = PasswordHash.recommended()

# FastAPI 会从 Authorization: Bearer <token> 中读取令牌。
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="auth/token",
)

# 正式环境必须通过环境变量设置密钥。
# 这里的默认值只用于本地学习，不能用于生产环境。
SECRET_KEY = os.getenv(
    "JWT_SECRET_KEY",
    "dev-only-secret-change-before-production",
)

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


def hash_password(password: str) -> str:
    """将明文密码转换为安全哈希。"""

    return password_hash.hash(password)


def verify_password(
    plain_password: str,
    hashed_password: str,
) -> bool:
    """验证输入密码是否匹配数据库中的哈希。"""

    return password_hash.verify(
        plain_password,
        hashed_password,
    )


def create_access_token(
    subject: str,
    expires_delta: timedelta | None = None,
) -> str:
    """创建带过期时间的 JWT 访问令牌。"""

    expire = datetime.now(timezone.utc) + (
        expires_delta
        or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    # sub 通常保存用户唯一标识，例如用户名或用户 ID。
    payload = {
        "sub": subject,
        "exp": expire,
    }

    return jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=ALGORITHM,
    )