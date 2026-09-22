from typing import Any, Literal

from pydantic import BaseModel, Field

from app.schemas.ai_workflow import AIWorkflowRunRead


AgentTask = Literal["auto", "reply", "tag", "schedule", "comprehensive"]
AgentExecutionMode = Literal["complete", "checkpointed"]
AgentControlAction = Literal["pause", "correct", "resume"]


class SalesAgentRequest(BaseModel):
    """销售 Agent 请求；auto 使用受控规划器，任何结果都不代表自动发送。"""

    task: AgentTask = "auto"
    instruction: str | None = Field(default=None, max_length=500)
    # checkpointed 模式让人工在每批只读工具之间检查并修正计划。
    execution_mode: AgentExecutionMode = "complete"
    idempotency_key: str | None = Field(default=None, min_length=8, max_length=100, pattern=r"^[A-Za-z0-9._:-]+$")


class AgentCorrection(BaseModel):
    """人工对综合 Agent 计划做的安全修正；只能跳过白名单工具。"""

    skip_tools: list[str] = Field(default_factory=list, max_length=5)
    note: str | None = Field(default=None, max_length=300)


class AgentControlRequest(BaseModel):
    """控制一次已创建的综合 Agent 运行，不触发消息发送。"""

    action: AgentControlAction
    correction: AgentCorrection | None = None
    # 每次最多执行多少个未完成步骤；默认一步，便于观察 Agent 轨迹。
    step_limit: int = Field(default=1, ge=1, le=5)


class AgentRetryRequest(BaseModel):
    """失败 Agent 的显式人工重试确认。"""

    confirm: bool = Field(default=False, description="必须明确确认本次可能再次调用模型")


class AgentToolTrace(BaseModel):
    name: str
    status: Literal["ok", "skipped", "incomplete", "error"]
    detail: str


class AgentStepRead(BaseModel):
    """一个只读工具步骤的可审计摘要；不暴露聊天原文或模型密钥。"""

    step: int
    tool_name: str
    status: Literal["ok", "skipped", "incomplete", "error"]
    summary: str
    data: dict[str, Any] = Field(default_factory=dict)
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    missing_inputs: list[str] = Field(default_factory=list)


class SalesAgentRead(BaseModel):
    agent_name: str
    # wait 表示规则已判断当前会话正等待客户回复，不会调用模型生成重复草稿。
    intent: Literal["reply", "tag", "schedule", "comprehensive", "wait"]
    selected_tool: str
    planned_by: Literal["bailian", "mock", "explicit_task", "rule_based"]
    planner_run_id: int | None = None
    human_confirmation_required: bool = True
    tool_trace: list[AgentToolTrace]
    steps: list[AgentStepRead] = Field(default_factory=list)
    workflow: AIWorkflowRunRead

    # 预留安全的可扩展元数据，不放入客户原始聊天正文。
    metadata: dict[str, Any] = Field(default_factory=dict)
