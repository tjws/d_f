from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class AuditLogRead(BaseModel):
    """返回给管理员查看的审计日志。"""

    id: int
    actor_user_id: int | None
    actor_username_snapshot: str | None
    actor_role_snapshot: str | None
    actor_source: str
    action: str
    target_type: str
    target_id: str
    detail_json: dict[str, Any] | None
    result: str
    ip_address: str | None
    request_id: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AuditLogListResponse(BaseModel):
    """审计日志分页响应。"""

    items: list[AuditLogRead]
    total: int
    page: int
    page_size: int
