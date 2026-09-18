from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


RetentionDataset = Literal["chat_messages", "ai_feedback"]


class RetentionDatasetPolicy(BaseModel):
    dataset: str
    retention_days: int
    automatic_deletion_allowed: bool
    note: str


class RetentionPolicyRead(BaseModel):
    automatic_deletion_enabled: bool
    configured_at: str
    datasets: list[RetentionDatasetPolicy]
    non_deletable_datasets: list[str]
    note: str


class RetentionPreviewRequest(BaseModel):
    dataset: RetentionDataset
    before: datetime | None = None


class RetentionPreviewRead(BaseModel):
    dataset: str
    before: datetime
    matching_rows: int
    oldest_created_at: datetime | None
    newest_created_at: datetime | None
    deletion_allowed: bool


class RetentionPurgeRequest(BaseModel):
    dataset: RetentionDataset
    before: datetime | None = None
    confirm: bool = Field(default=False, description="必须显式确认才允许清理")


class RetentionPurgeRead(BaseModel):
    dataset: str
    before: datetime
    deleted_rows: int
    audit_log_id: int | None
