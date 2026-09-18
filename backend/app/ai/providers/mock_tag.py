from app.ai.providers.base import TagSuggestionCandidate, TagSuggestionPayload


class MockTagProvider:
    """本地规则标签 Provider；标签仍需人工确认后才生效。"""

    def generate(self, context: dict[str, object]) -> TagSuggestionPayload:
        customer = context.get("customer")
        profile = context.get("confirmed_profile")
        if not isinstance(customer, dict):
            raise ValueError("customer context is required")

        candidates: list[TagSuggestionCandidate] = []
        customer_id = str(customer.get("id", ""))
        subject = customer.get("interested_subject")
        if isinstance(subject, str) and subject:
            # 标签 key 必须稳定，不能直接把任意用户输入拼进系统标识。
            subject_keys = {
                "数学": "subject_math",
                "英语": "subject_english",
                "语文": "subject_chinese",
                "物理": "subject_physics",
                "化学": "subject_chemistry",
            }
            candidates.append(
                {
                    "key": subject_keys.get(subject, "subject_other"),
                    "name": f"{subject}兴趣",
                    "category": "学习兴趣",
                    "description": "客户明确关注的学科",
                    "color": "#3B82F6",
                    "evidence": [
                        {
                            "source_type": "customer",
                            "source_id": customer_id,
                            "fact": "客户明确关注的学科",
                        }
                    ],
                }
            )

        if customer.get("stage") == "following_up":
            candidates.append(
                {
                    "key": "follow_up_active",
                    "name": "需要持续跟进",
                    "category": "销售阶段",
                    "description": "客户处于跟进阶段",
                    "color": "#F59E0B",
                    "evidence": [
                        {
                            "source_type": "customer",
                            "source_id": customer_id,
                            "fact": "客户处于跟进阶段",
                        }
                    ],
                }
            )

        if isinstance(profile, dict):
            dimensions = profile.get("dimensions", {})
            student_count = dimensions.get("student_count", 0) if isinstance(dimensions, dict) else 0
            if isinstance(student_count, int) and student_count > 0:
                candidates.append(
                    {
                        "key": "has_student_profile",
                        "name": "已有学生资料",
                        "category": "资料完整度",
                        "description": "客户已有学生资料可供分析",
                        "color": "#10B981",
                        "evidence": [
                            {
                                "source_type": "customer_profile",
                                "source_id": str(profile.get("id", "")),
                                "fact": "客户已有学生资料可供分析",
                            }
                        ],
                    }
                )

        return {
            "candidates": candidates,
            "model_name": "mock-rules",
            "model_version": "1",
        }
