"""多工具结果的安全汇总器。

第一版使用确定性模板把工具证据整理成草稿，避免在开发阶段为每次汇总额外调用模型；后续可替换为
百炼 JSON Provider，但仍需保留缺失信息和人工确认字段。
"""

from typing import Any


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def synthesize_comprehensive_suggestion(
    customer: dict[str, Any],
    steps: list[dict[str, Any]],
) -> dict[str, Any]:
    """把五个查询步骤合并为一条待人工编辑的回复草稿。"""

    missing_inputs = _unique(
        [
            str(value)
            for step in steps
            for value in step.get("missing_inputs", [])
            if isinstance(step, dict)
        ]
    )
    errors = [step for step in steps if step.get("status") == "error"]
    titles = [
        str(title)
        for step in steps
        for title in (step.get("data", {}).get("titles", []) if isinstance(step.get("data"), dict) else [])
    ]
    subject = str(customer.get("interested_subject") or "孩子当前关注的课程")
    uncertainty = "high" if missing_inputs or errors else "normal"
    if errors:
        text = "部分资料查询失败，暂时不能形成完整判断。请先核对查询结果，再由人工决定是否回复家长。"
    elif not titles:
        text = f"关于{subject}，我已整理现有客户资料和课程信息；具体价格、名额与适配情况需要我人工核实后再回复您。"
    else:
        text = f"关于{subject}，我已根据已审核资料整理了初步信息（{titles[0]}）。具体课程安排和名额需要我再人工核实，确认后回复您。"
    return {
        "content": {
            "text": text,
            "tone": "professional",
            "purpose": "comprehensive_follow_up",
            "uncertainty": uncertainty,
            "missing_inputs": missing_inputs,
        },
        "evidence": [
            evidence
            for step in steps
            for evidence in step.get("evidence", [])
            if isinstance(step, dict) and isinstance(evidence, dict)
        ][:20],
        "evidence_level": "insufficient" if missing_inputs or errors else "sufficient",
        "model_name": "agent-orchestrator",
        "model_version": "comprehensive-v1",
    }


__all__ = ["synthesize_comprehensive_suggestion"]
