from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


DataExportDataset = Literal["customers", "chat_messages", "audit_logs", "ai_feedback"]
DataExportFormat = Literal["csv", "json"]


class DataRetentionPolicyRead(BaseModel):
    automatic_deletion_enabled: bool
    default_export_redacted: bool
    requires_admin: bool
    review_before_delete: bool
    datasets: list[str]
    note: str
    retention_days: dict[str, int] = Field(default_factory=dict)


class DataExportQuery(BaseModel):
    dataset: DataExportDataset
    output_format: DataExportFormat
    start: datetime | None
    end: datetime | None
    limit: int
