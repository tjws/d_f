"""AI 工作流任务入口。

max_retries=0 是成本边界：模型调用失败不会被任务框架悄悄重复执行。
用户可在界面上决定是否再次点击生成。
"""

import dramatiq

from app.services.ai_workflow_service import execute_ai_workflow_run
from app.services.comprehensive_agent_service import execute_comprehensive_agent_run
from app.workers.broker import broker  # noqa: F401 先配置 broker，再声明 actor。
from app.workers.knowledge_tasks import index_knowledge_document_task  # noqa: F401 注册知识库索引任务。


@dramatiq.actor(queue_name="ai_workflow", max_retries=0, time_limit=30_000)
def execute_ai_workflow_task(run_id: int) -> None:
    execute_ai_workflow_run(run_id)


@dramatiq.actor(queue_name="ai_workflow", max_retries=0, time_limit=30_000)
def execute_comprehensive_agent_task(run_id: int) -> None:
    """执行综合 Agent；每个只读工具边界都会回写 PostgreSQL 检查点。"""

    execute_comprehensive_agent_run(run_id)
