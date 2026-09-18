"""HTTP 请求与业务日志共享的轻量上下文。"""

from contextvars import ContextVar


request_id_var: ContextVar[str] = ContextVar("request_id", default="-")
actor_user_id_var: ContextVar[int | None] = ContextVar("actor_user_id", default=None)


def set_request_id(value: str):
    return request_id_var.set(value)


def set_actor_user_id(value: int | None):
    return actor_user_id_var.set(value)
