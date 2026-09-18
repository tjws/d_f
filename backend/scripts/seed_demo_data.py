"""创建可重复执行的本地演示数据。

默认只预览，不写数据库；加 --apply 才会写入当前 DATABASE_URL 指向的库。
脚本只生成假数据，密码仅用于本地演示，绝不能用于生产环境。
"""

import argparse
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.core.crypto import encrypt_text
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.ai_suggestion import AISuggestion
from app.models.ai_suggestion_feedback import AISuggestionFeedback
from app.models.ai_workflow_run import AIWorkflowRun
from app.models.chat_message import ChatMessage
from app.models.customer import Customer
from app.models.course_order import CourseOrder
from app.models.customer_profile import CustomerProfile
from app.models.customer_tag import CustomerTag
from app.models.organization import Organization
from app.models.schedule import Schedule
from app.models.sales_script import SalesScript
from app.models.service_ticket import ServiceTicket
from app.models.student import Student
from app.models.tag import Tag
from app.models.timeline_event import TimelineEvent
from app.models.user import User
from app.models.knowledge_document import KnowledgeDocument
from app.models.knowledge_chunk import KnowledgeChunk


DEMO_PASSWORD = "Demo123456!"

# 固定的 Mock 媒体引用只用于本地演示；真正的企业微信媒体对象不会写入种子数据。
DEMO_VOICE_KEY = "mock-voice:家长想了解数学课程和试听时间"


def _user(
    db,
    username: str,
    role: str,
    full_name: str,
    organization_id: int,
    *,
    reset_demo_password: bool = False,
) -> User:
    user = db.scalar(select(User).where(User.username == username))
    if user is None:
        user = User(username=username, full_name=full_name, role=role, organization_id=organization_id, hashed_password=hash_password(DEMO_PASSWORD), wecom_userid=f"mock-{username}")
        db.add(user); db.flush()
    elif reset_demo_password:
        # 仅 --apply 时重置固定演示账号，避免预览或生产账号被脚本修改。
        user.hashed_password = hash_password(DEMO_PASSWORD)
    return user


def _ensure_timeline_event(
    db,
    *,
    customer_id: int,
    operator_id: int | None,
    event_type: str,
    source: str,
    summary: str,
    reference_type: str | None,
    reference_id: str | None,
    occurred_at: datetime,
) -> None:
    """按引用定位时间线事件，避免重复运行 seed 造成重复记录。"""

    statement = select(TimelineEvent).where(
        TimelineEvent.customer_id == customer_id,
        TimelineEvent.event_type == event_type,
        TimelineEvent.reference_type == reference_type,
        TimelineEvent.reference_id == reference_id,
    )
    existing = db.scalar(statement)
    if existing is None:
        db.add(
            TimelineEvent(
                customer_id=customer_id,
                operator_id=operator_id,
                event_type=event_type,
                source=source,
                summary_encrypted=encrypt_text(summary),
                reference_type=reference_type,
                reference_id=reference_id,
                occurred_at=occurred_at,
            )
        )
    else:
        # 仅针对固定演示事件刷新已知假摘要，兼容本地加密密钥更换后的开发库。
        existing.summary_encrypted = encrypt_text(summary)


def _ensure_demo_message(
    db,
    *,
    customer: Customer,
    sales: User,
    external_id: str,
    direction: str,
    message_type: str,
    content: str | None,
    media_object_key: str | None,
    sent_at: datetime,
    reset_voice: bool = False,
) -> ChatMessage:
    """补一条 Mock 消息，并为侧边栏建立对应的时间线事件。"""

    message = db.scalar(
        select(ChatMessage).where(ChatMessage.wecom_message_id == external_id)
    )
    if message is None:
        message = ChatMessage(
            customer_id=customer.id,
            user_id=sales.id,
            wecom_message_id=external_id,
            direction=direction,
            message_type=message_type,
            content_encrypted=encrypt_text(content) if content is not None else None,
            content_masked=content,
            media_object_key=media_object_key,
            sent_at=sent_at,
        )
        db.add(message)
        db.flush()
    elif message_type == "text":
        # 演示资料允许在密钥轮换后用已知假内容重新加密，避免旧开发密钥导致页面 500。
        message.content_encrypted = encrypt_text(content) if content is not None else None
        message.content_masked = content
        message.media_object_key = media_object_key
    elif message_type == "voice" and message.media_object_key == DEMO_VOICE_KEY and message.content_encrypted is not None:
        # 若用户之前点过 Mock 转写，同样可以用确定的 Mock 文本修复本地密钥变化。
        transcript = DEMO_VOICE_KEY.removeprefix("mock-voice:").strip()
        message.content_encrypted = encrypt_text(transcript)
        message.content_masked = transcript
    if reset_voice and message_type == "voice":
        message.content_encrypted = None
        message.content_masked = None
        db.query(TimelineEvent).filter(
            TimelineEvent.customer_id == customer.id,
            TimelineEvent.event_type == "voice_transcribed",
            TimelineEvent.reference_type == "chat_message",
            TimelineEvent.reference_id == str(message.id),
        ).delete(synchronize_session=False)
    _ensure_timeline_event(
        db,
        customer_id=customer.id,
        operator_id=sales.id,
        event_type="wecom_message",
        source="wecom",
        summary=content or "收到一条语音消息（等待人工转写）",
        reference_type="chat_message",
        reference_id=str(message.id),
        occurred_at=sent_at,
    )
    return message


def seed(apply: bool, *, reset_voice: bool = False) -> None:
    with SessionLocal() as db:
        org = db.scalar(select(Organization).where(Organization.name == "演示教育中心"))
        if org is None:
            org = Organization(name="演示教育中心", type="team", status="active")
            db.add(org); db.flush()
        admin = _user(db, "demo_admin", "admin", "演示管理员", org.id, reset_demo_password=apply)
        manager = _user(db, "demo_manager", "manager", "演示经理", org.id, reset_demo_password=apply)
        sales = _user(db, "demo_sales", "sales", "演示销售", org.id, reset_demo_password=apply)
        if not apply:
            print("预览：将确保 1 个组织、3 个用户、3 个客户、学生、聊天/语音、订单/工单、AI 建议和知识库演示资料存在。")
            print(f"本地演示账号：demo_admin / {DEMO_PASSWORD}")
            db.rollback(); return

        customers = []
        specs = [("林女士", "13800000001", "小林", "初一", "数学", "new"), ("周先生", "13800000002", "小周", "五年级", "英语", "following_up"), ("陈女士", "13800000003", "小陈", "高一", "语文", "converted")]
        for name, phone, student_name, grade, subject, stage in specs:
            customer = db.scalar(select(Customer).where(Customer.phone == phone))
            if customer is None:
                customer = Customer(owner_id=sales.id, name=name, phone=phone, student_name=student_name, grade=grade, interested_subject=subject, stage=stage, source="demo-seed", remark="[demo-seed] 可安全删除的演示客户")
                db.add(customer); db.flush()
            elif customer.source == "demo-seed" and customer.owner_id is None:
                customer.owner_id = sales.id
            customers.append(customer)

        students_by_customer: dict[int, Student] = {}
        for index, customer in enumerate(customers):
            student = db.scalar(select(Student).where(Student.customer_id == customer.id).order_by(Student.id))
            if student is None:
                student = Student(customer_id=customer.id, name_encrypted=encrypt_text(customer.student_name or "演示学生"), grade=customer.grade, school_encrypted=encrypt_text("演示学校"), subjects_json={"primary": customer.interested_subject})
                db.add(student)
                db.flush()
            elif customer.source == "demo-seed":
                # 演示姓名/学校是脚本已知的假数据，可在本地密钥更换后安全重加密。
                student.name_encrypted = encrypt_text(customer.student_name or "演示学生")
                student.school_encrypted = encrypt_text("演示学校")
                student.grade = customer.grade
                student.subjects_json = {"primary": customer.interested_subject}
            students_by_customer[customer.id] = student

            now = datetime.now(timezone.utc) - timedelta(days=index)
            _ensure_demo_message(
                db, customer=customer, sales=sales, external_id=f"demo-{customer.id}-0",
                direction="inbound", message_type="text", content="您好，想了解试听课和收费。",
                media_object_key=None, sent_at=now,
            )
            _ensure_demo_message(
                db, customer=customer, sales=sales, external_id=f"demo-{customer.id}-1",
                direction="outbound", message_type="text", content="您好，我先了解孩子的年级和学习目标，再为您安排合适方案。",
                media_object_key=None, sent_at=now + timedelta(minutes=1),
            )
            # 语音保持“未转写”状态，页面可用 Mock 转写按钮验证人工触发闭环。
            _ensure_demo_message(
                db, customer=customer, sales=sales, external_id=f"demo-{customer.id}-voice-001",
                direction="inbound", message_type="voice", content=None,
                media_object_key=DEMO_VOICE_KEY, sent_at=now + timedelta(minutes=2), reset_voice=reset_voice,
            )
            _ensure_timeline_event(
                db, customer_id=customer.id, operator_id=sales.id,
                event_type="demo_seed", source="system", summary="已生成演示聊天、语音和时间线资料",
                reference_type="customer", reference_id=str(customer.id), occurred_at=now,
            )
            if db.scalar(select(CustomerProfile.id).where(CustomerProfile.customer_id == customer.id)) is None:
                profile = CustomerProfile(customer_id=customer.id, version=1, status="confirmed", dimensions_json={"learning_goal": "提升学习稳定性", "next_action": "安排一次针对性试听"}, evidence_json=[{"source_type": "demo", "fact": "演示资料"}], confirmed_by=manager.id, confirmed_at=datetime.now(timezone.utc))
                db.add(profile); db.flush()
                db.add(AISuggestion(customer_id=customer.id, user_id=sales.id, profile_id=profile.id, suggestion_type="reply", content_json={"text": "您好，我可以先为孩子安排一次针对性试听，您周末哪个时间方便？", "tone": "professional", "purpose": "follow_up"}, evidence_json=[{"source_type": "knowledge", "source_id": "02_math_trial"}], evidence_level="normal", status="draft"))

        # 为管理看板准备少量可解释的演示统计；这些记录只代表建议和工作流状态，不代表自动发送。
        analytics_specs = [
            (customers[0], "tag", "accepted", "重点关注数学"),
            (customers[1], "schedule", "edited", "建议人工确认周末试听时间"),
            (customers[2], "reply", "rejected", "暂不发送，等待补充学生目标"),
        ]
        for customer, suggestion_type, action, text in analytics_specs:
            # 同一客户可能已经有工作流生成的同类型草稿；只复用本脚本自己打的标记。
            suggestion = next(
                (
                    item
                    for item in db.scalars(
                        select(AISuggestion).where(
                            AISuggestion.customer_id == customer.id,
                            AISuggestion.suggestion_type == suggestion_type,
                        )
                    )
                    if (item.content_json or {}).get("purpose") == "demo_dashboard"
                ),
                None,
            )
            if suggestion is None:
                suggestion = AISuggestion(
                    customer_id=customer.id,
                    user_id=sales.id,
                    suggestion_type=suggestion_type,
                    content_json={"text": text, "purpose": "demo_dashboard"},
                    evidence_json=[{"source_type": "demo", "source_id": "seed_demo_data"}],
                    evidence_level="normal",
                    status="edited" if action == "edited" else action,
                    model_name="mock-rules",
                    model_version="demo-1",
                    prompt_version=f"{suggestion_type}-demo-v1",
                    decided_by=sales.id,
                    decided_at=datetime.now(timezone.utc),
                )
                if action == "edited":
                    suggestion.edited_content_json = {"text": f"{text}（已人工编辑）"}
                db.add(suggestion)
                db.flush()
            if db.scalar(select(AISuggestionFeedback).where(AISuggestionFeedback.target_type == suggestion_type, AISuggestionFeedback.target_id == str(suggestion.id))) is None:
                db.add(AISuggestionFeedback(
                    suggestion_id=suggestion.id,
                    customer_id=customer.id,
                    actor_user_id=sales.id,
                    action=action,
                    edited_content=suggestion.edited_content_json,
                    target_type=suggestion_type,
                    target_id=str(suggestion.id),
                ))

        workflow_specs = [
            (customers[0], "succeeded", "reply", "demo-success"),
            (customers[1], "waiting_human", "schedule", "demo-waiting"),
            (customers[2], "failed", "tag", "demo-failed"),
        ]
        for customer, status, goal, marker in workflow_specs:
            if db.scalar(select(AIWorkflowRun).where(AIWorkflowRun.customer_id == customer.id, AIWorkflowRun.result_json["demo_marker"].as_string() == marker)) is None:
                now = datetime.now(timezone.utc)
                db.add(AIWorkflowRun(
                    customer_id=customer.id,
                    actor_user_id=sales.id,
                    goal=goal,
                    provider_name="mock",
                    status=status,
                    attempt_count=1,
                    result_json={"demo_marker": marker, "suggestion_only": True},
                    error_code="demo_provider_error" if status == "failed" else None,
                    created_at=now - timedelta(minutes=5),
                    started_at=now - timedelta(minutes=4),
                    finished_at=None if status == "waiting_human" else now - timedelta(minutes=3),
                ))
        for key, name, category, color in (("needs_trial", "有试听意向", "意向", "#2563eb"), ("math_focus", "数学关注", "学科", "#7c3aed"), ("followup_weekend", "周末跟进", "节奏", "#0f766e")):
            if db.scalar(select(Tag.id).where(Tag.key == key)) is None:
                db.add(Tag(key=key, name=name, category=category, color=color, description="演示标签"))
        db.flush()
        trial_tag = db.scalar(select(Tag).where(Tag.key == "needs_trial"))
        if trial_tag is not None and db.scalar(select(CustomerTag.id).where(CustomerTag.customer_id == customers[0].id, CustomerTag.tag_id == trial_tag.id)) is None:
            db.add(CustomerTag(customer_id=customers[0].id, tag_id=trial_tag.id, source="manual", status="confirmed", created_by=sales.id, confirmed_by=sales.id, confirmed_at=datetime.now(timezone.utc), evidence_json=[{"source_type": "demo", "fact": "家长表达试听意向"}]))
        if db.scalar(select(Schedule.id).where(Schedule.customer_id == customers[0].id)) is None:
            db.add(Schedule(customer_id=customers[0].id, user_id=sales.id, title="演示试听课跟进", description="确认周末试听时间", due_at=datetime.now(timezone.utc) + timedelta(days=2), priority="normal", source="manual", status="confirmed", evidence_json=[{"source_type": "demo"}]))
        if db.scalar(select(CourseOrder.id).where(CourseOrder.external_order_id == "demo-order-001")) is None:
            db.add(CourseOrder(customer_id=customers[2].id, student_id=students_by_customer[customers[2].id].id, external_order_id="demo-order-001", course_name="高中语文进阶课", amount="2999.00", status="paid", ordered_at=datetime.now(timezone.utc) - timedelta(days=3), raw_snapshot_json={"source": "demo-seed", "status": "paid"}))
        _ensure_timeline_event(
            db, customer_id=customers[2].id, operator_id=sales.id,
            event_type="order_created", source="system", summary="已生成演示已支付订单",
            reference_type="course_order", reference_id="demo-order-001",
            occurred_at=datetime.now(timezone.utc) - timedelta(days=3),
        )
        if db.scalar(select(ServiceTicket.id).where(ServiceTicket.external_ticket_id == "demo-ticket-001")) is None:
            db.add(ServiceTicket(customer_id=customers[1].id, external_ticket_id="demo-ticket-001", type="课程咨询", status="open", summary_encrypted=encrypt_text("家长希望调整试听时间"), opened_at=datetime.now(timezone.utc) - timedelta(hours=6), raw_snapshot_json={"source": "demo-seed", "status": "open"}))
        else:
            existing_ticket = db.scalar(select(ServiceTicket).where(ServiceTicket.external_ticket_id == "demo-ticket-001"))
            if existing_ticket is not None:
                existing_ticket.summary_encrypted = encrypt_text("家长希望调整试听时间")
        _ensure_timeline_event(
            db, customer_id=customers[1].id, operator_id=sales.id,
            event_type="service_ticket_created", source="system", summary="已生成演示服务工单",
            reference_type="service_ticket", reference_id="demo-ticket-001",
            occurred_at=datetime.now(timezone.utc) - timedelta(hours=6),
        )
        # 话术库使用可重复写入的固定演示资料；只有 published 版本会被 AI context builder 使用。
        demo_scripts = [
            ("reply", "new", "", "试听邀约", "可以先安排一次针对性试听，了解孩子的学习目标后再推荐课程。您本周末哪个时间方便？", "professional"),
            ("objection", "following_up", "价格", "价格异议回应", "理解您对预算的考虑。我们可以先从试听和学习目标评估开始，再一起选择合适的课程方案。", "empathetic"),
            ("follow_up", "following_up", "", "温和跟进", "上次沟通的学习方案还需要我补充哪些信息？如果方便，我可以按您的时间安排下一次沟通。", "concise"),
        ]
        for scene, stage, objection, title, content, tone in demo_scripts:
            script = db.scalar(select(SalesScript).where(SalesScript.title == title))
            if script is None:
                db.add(SalesScript(scene=scene, customer_stage=stage, objection_type=objection or None, title=title, content=content, tone=tone, status="published", version=1, created_by=manager.id, approved_by=manager.id))
        demo_knowledge = [
            ("course_overview_demo", "K12 课程沟通总览", "课程", ["首次沟通先确认年级、学习目标、近期表现和可投入时间，再解释课程适配逻辑；不要承诺固定提分幅度。", "课程介绍应先讲适配条件和学习路径，再说明服务内容，不能把单一案例当作普遍结果。"]),
            ("trial_process_demo", "试听课标准流程", "试听", ["试听课建议包含目标了解、专题讲解、练习和共同总结。试听后只记录观察到的学习习惯与下一步建议，不把体验课包装成诊断结论。", "试听结束后由销售人工确认家长是否愿意继续沟通，AI 只能提供待确认的跟进建议。"]),
            ("parent_objection_demo", "家长异议处理", "沟通", ["家长关注价格时，先确认预算和目标，再说明试听、评估与课程方案的关系；表达要尊重，不使用夸大承诺。", "遇到效果、退费或合同问题时，只引用已审核的政策资料，不能自行承诺结果。"]),
            ("followup_policy_demo", "跟进记录规范", "跟进", ["每次跟进记录沟通事实、家长提出的问题和下一步动作。涉及时间安排时，先人工确认具体时段、参与人和渠道。", "时间线记录应区分家长原话、销售动作和 AI 建议，避免把建议误写成已经发生的事实。"]),
            ("subject_methods_demo", "分学科学习方法", "学习方法", ["数学关注概念理解、错题归因和分层练习；英语结合词汇、阅读和听力；语文关注信息提取、作文结构和修改反馈。", "学科建议要结合学生年级和已确认资料，缺少证据时应先询问，而不是编造薄弱项。"]),
            ("privacy_and_safety_demo", "隐私与安全沟通", "合规", ["客户联系方式、学生姓名和学校属于敏感信息，只在授权范围内展示；日志和 AI 上下文使用脱敏内容。", "不要在普通运行日志、知识库或 AI 建议中写入密码、JWT、百炼 Key 或完整聊天敏感正文。"]),
            ("schedule_confirmation_demo", "日程确认规范", "日程", ["AI 可以建议下一次联系时间，但必须由人工确认日期、时区、参与人和渠道后才创建正式日程。", "日程冲突或家长未确认时，保留为待确认建议，不得自动发送提醒。"]),
            ("service_ticket_demo", "服务工单处理", "售后", ["工单先记录事实和外部编号，再按 open、in_progress、closed 的状态流转；关闭前应填写处理结果。", "真实外部工单尚未接入时只能使用 Mock 同步，重复外部编号必须幂等跳过。"]),
        ]
        for slug, title, category, chunks in demo_knowledge:
            document = db.scalar(select(KnowledgeDocument).where(KnowledgeDocument.slug == slug))
            if document is None:
                document = KnowledgeDocument(slug=slug, title=title, category=category, source="demo-seed", status="published", version=1, created_by=manager.id, published_by=manager.id, published_at=datetime.now(timezone.utc))
                db.add(document)
                db.flush()
            existing_chunks = {chunk.chunk_index for chunk in document.chunks}
            for index, content in enumerate(chunks):
                if index not in existing_chunks:
                    db.add(KnowledgeChunk(document_id=document.id, chunk_index=index, content=content, keywords=category))
        db.commit()
        print("演示数据已写入当前 DATABASE_URL 指向的数据库。")
        print(f"本地演示账号：demo_admin / {DEMO_PASSWORD}（另有 demo_manager、demo_sales，密码相同）")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed safe local demo data")
    parser.add_argument("--apply", action="store_true", help="确认写入数据库；默认仅预览")
    parser.add_argument("--reset-voice", action="store_true", help="清除固定演示语音的转写结果，恢复到待人工转写")
    args = parser.parse_args()
    if args.reset_voice and not args.apply:
        parser.error("--reset-voice 必须与 --apply 一起使用")
    seed(args.apply, reset_voice=args.reset_voice)
