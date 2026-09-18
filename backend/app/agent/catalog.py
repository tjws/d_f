"""本地演示用课程/开班静态资料。

这里故意不提供实时座位数，也不接入真实排课系统；真实库存接入前，结果必须标记为“需人工核实”。
"""

from typing import Any


COURSE_OPENINGS: tuple[dict[str, str], ...] = (
    {
        "course_name": "初一数学基础提升班",
        "subject": "数学",
        "grade_range": "初一",
        "schedule": "周六 09:00-11:00",
        "mode": "小班面授",
        "availability": "需人工核实",
    },
    {
        "course_name": "初高中英语阅读方法课",
        "subject": "英语",
        "grade_range": "初一-高三",
        "schedule": "周日 14:00-16:00",
        "mode": "线上小班",
        "availability": "需人工核实",
    },
    {
        "course_name": "小学语文阅读与写作",
        "subject": "语文",
        "grade_range": "小学三-六年级",
        "schedule": "周六 14:00-16:00",
        "mode": "小班面授",
        "availability": "需人工核实",
    },
)


def list_course_openings(subject: str | None = None, grade: str | None = None) -> list[dict[str, Any]]:
    """按客户关注条件筛选静态开班资料，并明确不能代替实时库存查询。"""

    normalized_subject = (subject or "").strip()
    normalized_grade = (grade or "").strip()
    items = [
        dict(item)
        for item in COURSE_OPENINGS
        if (not normalized_subject or normalized_subject in item["subject"])
        and (not normalized_grade or normalized_grade in item["grade_range"])
    ]
    return items or [dict(item) for item in COURSE_OPENINGS]


__all__ = ["COURSE_OPENINGS", "list_course_openings"]
