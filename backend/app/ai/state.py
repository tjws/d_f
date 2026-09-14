from typing import Literal, TypedDict


class CustomerAIState(TypedDict, total=False):
    """客户 AI 工作流在各个 LangGraph 节点之间传递的状态。"""

    # 当前客户，后续节点都围绕这个客户工作
    customer_id: int

    # 触发本轮工作流的内部用户，用于权限校验和审计归属
    actor_user_id: int

    # 经过脱敏后的客户上下文，不能放入明文敏感数据
    context: dict[str, object]

    # 当前工作流状态
    status: Literal[
        "pending",
        "context_ready",
        "suggestions_ready",
        "waiting_human",
        "failed",
    ]

    # 统一保存本轮生成的建议 ID
    suggestion_ids: list[int]

    # LangGraph 当前阶段只保存内存中的草稿，后续再交给持久化 Service。
    suggestions: list[dict[str, object]]

    # 发生异常时给测试和日志使用
    error: str
