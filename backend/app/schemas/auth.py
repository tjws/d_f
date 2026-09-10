from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class UserCreate(BaseModel):
    """注册用户时接收的数据。"""

    username: str = Field(
        min_length=3,
        max_length=50,
    )

    password: str = Field(
        min_length=8,
        max_length=128,
    )

    full_name: str | None = Field(
        default=None,
        max_length=100,
    )


class UserRead(BaseModel):
    """返回给前端的用户数据。"""

    id: int
    username: str
    full_name: str | None
    role: str
    is_active: bool
    created_at: datetime

    # 允许从 SQLAlchemy User 对象读取字段。
    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    """登录成功后返回的令牌。"""

    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """JWT 中解析出的用户标识。"""

    username: str | None = None