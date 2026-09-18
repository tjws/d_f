from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


PermissionRole = Literal["admin", "manager", "sales"]
PermissionScope = Literal["own", "team", "organization", "all"]


class AdminPermissionRead(BaseModel):
    id: int
    role: PermissionRole
    module: str
    action: str
    data_scope: PermissionScope
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AdminPermissionUpdate(BaseModel):
    data_scope: PermissionScope
