"""客户流失风险管理接口的输入输出结构。"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


ChurnBatchStatus = Literal["running", "completed", "failed"]
ChurnRiskLevel = Literal["high", "medium", "low"]
ChurnInterventionStatus = Literal["planned", "in_progress", "completed", "cancelled"]
ChurnInterventionOutcome = Literal["retained", "recovered", "churned", "unknown"]


class ChurnScoringBatchRead(BaseModel):
    id: int
    status: ChurnBatchStatus
    model_name: str
    model_schema_version: str
    model_version_id: int | None
    source_filename: str
    source_sha256: str
    source_system: str
    trigger_source: str
    observation_at: datetime | None
    decision_threshold: float
    medium_threshold: float
    row_count: int
    scored_count: int
    high_count: int
    medium_count: int
    low_count: int
    error_code: str | None
    drift_status: str
    drift: dict
    started_at: datetime
    finished_at: datetime | None
    created_at: datetime


class ChurnScoringBatchList(BaseModel):
    items: list[ChurnScoringBatchRead]
    total: int


class ChurnRiskPredictionRead(BaseModel):
    id: int
    student_external_id: str
    # API 使用 risk_score，避免把未校准分值宣传成真实流失概率。
    risk_score: float
    risk_level: ChurnRiskLevel
    predicted_churn: bool
    risk_rank: int
    risk_percentile: float
    mapping_id: int | None
    student_id: int | None
    customer_id: int | None
    customer_name: str | None
    owner_id: int | None
    mapping_status: Literal["mapped", "unmapped"]
    intervention: "ChurnInterventionRead | None" = None
    created_at: datetime


class ChurnRiskBatchDetail(BaseModel):
    batch: ChurnScoringBatchRead
    items: list[ChurnRiskPredictionRead]
    total: int
    page: int
    page_size: int


class ExternalStudentMappingCreate(BaseModel):
    source_system: str = Field(default="csv", min_length=1, max_length=50)
    external_student_id: str = Field(min_length=1, max_length=100)
    student_id: int


class ExternalStudentMappingRead(BaseModel):
    id: int
    source_system: str
    external_student_id: str
    student_id: int
    customer_id: int
    rebound_prediction_count: int = 0
    created_at: datetime


class ChurnInterventionCreate(BaseModel):
    action_type: Literal["phone_call", "mock_wecom", "trial_class", "learning_plan", "other"]
    due_at: datetime
    note: str | None = Field(default=None, max_length=500)


class ChurnInterventionUpdate(BaseModel):
    status: ChurnInterventionStatus
    outcome: ChurnInterventionOutcome | None = None
    note: str | None = Field(default=None, max_length=500)


class ChurnInterventionRead(BaseModel):
    id: int
    prediction_id: int
    customer_id: int
    student_id: int
    actor_user_id: int | None
    schedule_id: int | None
    action_type: str
    status: ChurnInterventionStatus
    outcome: ChurnInterventionOutcome | None
    note: str | None
    due_at: datetime
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ChurnModelRegister(BaseModel):
    artifact_filename: str = Field(min_length=1, max_length=255)
    report_filename: str | None = Field(default=None, max_length=255)
    version: str = Field(min_length=1, max_length=80)
    medium_threshold: float | None = None


class ChurnModelVersionRead(BaseModel):
    id: int
    version: str
    model_name: str
    schema_version: str
    artifact_filename: str
    artifact_sha256: str
    status: Literal["candidate", "approved", "retired"]
    decision_threshold: float
    medium_threshold: float
    metrics: dict
    approved_by: int | None
    approved_at: datetime | None
    created_at: datetime


class ChurnScoringRequest(BaseModel):
    source_filename: str = Field(min_length=1, max_length=255)
    source_system: str = Field(default="csv", min_length=1, max_length=50)
    model_version_id: int | None = None
    observation_at: datetime | None = None
    execution_mode: Literal["sync", "queue"] = "queue"


class ChurnScoringAccepted(BaseModel):
    status: Literal["completed", "queued", "duplicate"]
    batch_id: int | None = None
    message_id: str | None = None


ChurnRiskPredictionRead.model_rebuild()
