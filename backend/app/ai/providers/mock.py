from app.ai.providers.base import ReplySuggestionPayload
from app.knowledge.policy import fallback_reply_payload, should_use_fallback


class MockReplyProvider:
    """本地规则 Provider；用于开发和测试，不调用外部模型。"""

    def generate(self, context: dict[str, object]) -> ReplySuggestionPayload:
        customer = context.get("customer")
        confirmed_profile = context.get("confirmed_profile")

        if not isinstance(customer, dict) or not isinstance(confirmed_profile, dict):
            raise ValueError("confirmed_profile is required before reply suggestion")

        # 客观问题没有达到知识库阈值时，返回人工核实话术，不让规则或模型猜测答案。
        if should_use_fallback(context):
            return fallback_reply_payload(
                context,
                model_name="mock-rules",
                model_version="fallback-1",
            )

        dimensions = confirmed_profile.get("dimensions", {})
        if not isinstance(dimensions, dict):
            dimensions = {}

        subject = customer.get("interested_subject") or "当前关注的课程"
        next_action = dimensions.get("next_action") or "进一步了解学习目标"
        knowledge = context.get("knowledge", [])
        knowledge_hint = ""
        if isinstance(knowledge, list) and knowledge and isinstance(knowledge[0], dict):
            knowledge_hint = f" 我也可以按照《{knowledge[0].get('title', '课程资料')}》中的方案为您说明。"
        scripts = context.get("sales_scripts", [])
        script_hint = ""
        if isinstance(scripts, list) and scripts and isinstance(scripts[0], dict):
            script_hint = f" 可参考已审核话术《{scripts[0].get('title', '销售话术')}》。"
        completed_follow_ups = context.get("completed_follow_ups", [])
        follow_up_hint = ""
        if isinstance(completed_follow_ups, list) and completed_follow_ups and isinstance(completed_follow_ups[0], dict):
            latest = completed_follow_ups[0]
            outcome = str(latest.get("outcome", "other"))
            follow_up_hint = f" 上次人工跟进结果为“{outcome}”，这次可据此确认下一步安排。"
        content = {
            "text": (
                f"您好，结合孩子目前的情况，我们可以先围绕{subject}做一次针对性了解，"
                f"{next_action}，您看哪个时间方便沟通？{follow_up_hint}{knowledge_hint}{script_hint}"
            ),
            "tone": "professional",
            "purpose": "follow_up",
        }

        evidence: list[dict[str, object]] = [
            {
                "source_type": "customer_profile",
                "source_id": str(confirmed_profile.get("id", "")),
                "fact": "使用已确认客户画像",
            }
        ]
        messages = context.get("messages", [])
        if isinstance(messages, list):
            evidence.extend(
                {
                    "source_type": "chat_message",
                    "source_id": str(message.get("id", "")),
                    "fact": "参考最近聊天消息",
                }
                for message in messages[:5]
                if isinstance(message, dict)
            )

        timeline_events = context.get("timeline_events", [])
        if isinstance(timeline_events, list):
            evidence.extend(
                {
                    "source_type": "timeline_event",
                    "source_id": str(event.get("id", "")),
                    "fact": "参考客户时间线事件",
                }
                for event in timeline_events[:5]
                if isinstance(event, dict)
            )

        completed_follow_ups = context.get("completed_follow_ups", [])
        if isinstance(completed_follow_ups, list):
            evidence.extend(
                {
                    "source_type": "schedule_completion",
                    "source_id": str(item.get("id", "")),
                    "fact": f"参考人工回填跟进结果：{item.get('outcome', 'other')}",
                }
                for item in completed_follow_ups[:5]
                if isinstance(item, dict)
            )

        # 学生资料只作为可追溯证据，不把密文或完整敏感字段写入建议日志。
        students = context.get("students", [])
        if isinstance(students, list):
            evidence.extend(
                {
                    "source_type": "student",
                    "source_id": str(student.get("id", "")),
                    "fact": "参考已脱敏学生资料",
                }
                for student in students[:5]
                if isinstance(student, dict)
            )

        if isinstance(knowledge, list):
            evidence.extend(
                {
                    "source_type": "knowledge",
                    "source_id": f"{item.get('document_id', '')}:{item.get('chunk_id', '')}",
                    "fact": f"参考知识库《{item.get('title', '本地销售资料')}》",
                    "title": item.get("title", "本地销售资料"),
                    "chunk_id": item.get("chunk_id"),
                    "snippet": item.get("snippet", ""),
                }
                for item in knowledge[:5]
                if isinstance(item, dict)
            )

        if isinstance(scripts, list):
            evidence.extend(
                {"source_type": "sales_script", "source_id": str(item.get("id", "")), "fact": "参考已审核销售话术"}
                for item in scripts[:5]
                if isinstance(item, dict)
            )

        return {
            "content": content,
            "evidence": evidence,
            "evidence_level": "sufficient" if len(evidence) > 1 else "normal",
            "model_name": "mock-rules",
            "model_version": "1",
        }
