from typing import Literal


AgentGoal = Literal["reply", "tag", "schedule"]

_KEYWORDS: dict[AgentGoal, tuple[str, ...]] = {
    "tag": ("标签", "分类", "画像标签"),
    "schedule": ("日程", "跟进", "提醒", "预约"),
    "reply": ("回复", "话术", "怎么说", "回答"),
}


def choose_goal(task: str, instruction: str | None) -> AgentGoal:
    """把用户请求限制在三个已实现目标内；不允许 Agent 自由生成危险动作。"""

    if task in {"reply", "tag", "schedule"}:
        return task  # type: ignore[return-value]

    text = (instruction or "").strip()
    for goal, keywords in _KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            return goal
    return "reply"

