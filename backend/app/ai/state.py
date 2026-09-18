from typing import Literal, TypedDict


class CustomerAIState(TypedDict, total=False):
    """客户 AI 工作流在各个 LangGraph 节点之间传递的状态。"""

    # 当前客户，后续节点都围绕这个客户工作
    customer_id: int

    # 触发本轮工作流的内部用户，用于权限校验和审计归属
    actor_user_id: int

    # 调用方明确选择本轮需要的建议，避免一次运行自动生成全部内容。
    workflow_goal: Literal["profile", "reply", "tag", "schedule"]

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

    # 未确认画像时，本轮只会创建一份画像草稿并把其 ID 返回给前端。
    profile_id: int

    # 明确告诉调用方下一次必须由人工完成什么动作，避免 AI 自动跨越确认边界。
    next_action: Literal[
        "confirm_profile",
        "review_reply",
        "confirm_tags",
        "review_schedule",
    ]

    # LangGraph 当前阶段只保存内存中的草稿，后续再交给持久化 Service。
    suggestions: list[dict[str, object]]

    # 画像 Provider 输出的内存草稿，持久化节点写入数据库后才对用户可见。
    profile_draft: dict[str, object]

    # 标签和日程各自的 Provider 草稿，分别由对应持久化节点处理。
    tag_payload: dict[str, object]
    schedule_suggestion: dict[str, object]

    # 标签不是 AISuggestion，单独返回客户标签记录 ID。
    customer_tag_ids: list[int]

    # 发生异常时给测试和日志使用
    error: str
