from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class RuntimeDependencyStatus(BaseModel):
    status: Literal["ok", "error", "disabled"]


class AIProviderStatus(BaseModel):
    default_provider: str
    workflow_providers: dict[str, str]
    embedding_provider: str
    embedding_model: str
    bailian_api_key_configured: bool


class WorkerStatus(BaseModel):
    required: bool
    status: Literal["online", "offline", "error", "disabled"]
    worker_id: str | None
    last_seen_at: datetime | None
    queue_depths: dict[str, int]


class BackupStatus(BaseModel):
    configured: bool
    directory: str
    latest_backup_at: datetime | None
    latest_backup_name: str | None
    latest_size_bytes: int | None
    age_seconds: int | None
    status: Literal["ok", "missing", "stale", "disabled"]
    max_age_hours: int
    automatic_prune_enabled: bool


class SystemStatusRead(BaseModel):
    checked_at: datetime
    ready: bool
    dependencies: dict[str, RuntimeDependencyStatus]
    ai: AIProviderStatus
    worker: WorkerStatus
    backup: BackupStatus
