from fastapi import HTTPException, status
import logging
from sqlalchemy.orm import Session

from app.dao.ai_suggestion_feedback_dao import AISuggestionFeedbackDAO
from app.dao.ai_workflow_run_dao import AIWorkflowRunDAO
from app.models.ai_suggestion import AISuggestion
from app.models.ai_suggestion_feedback import AISuggestionFeedback
from app.models.user import User
from app.services.audit_log_service import append_audit_log
from app.services.customer_service import get_customer_or_404


feedback_dao = AISuggestionFeedbackDAO()
logger = logging.getLogger("k12.ai")
ALLOWED_TARGET_TYPES = {"profile", "reply", "tag", "schedule"}
ALLOWED_ACTIONS = {"accepted", "edited", "rejected"}
ALLOWED_AGENT_ACTIONS = {"incorrect_reasoning", "missing_information", "not_useful"}
workflow_run_dao = AIWorkflowRunDAO()


def record_target_feedback(
    db: Session,
    customer_id: int,
    actor: User,
    target_type: str,
    target_id: str,
    action: str,
    edited_content: dict | None = None,
    suggestion_id: int | None = None,
) -> AISuggestionFeedback:
    """在建议状态变更的同一事务中更新反馈，重复请求保持幂等。"""

    if customer_id <= 0 or actor.id <= 0:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="AI 建议关联信息无效")
    if target_type not in ALLOWED_TARGET_TYPES or not target_id:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="AI 反馈目标无效")
    if action not in ALLOWED_ACTIONS:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="AI 反馈操作无效")
    feedback = feedback_dao.get_by_target(db, customer_id, target_type, target_id)
    if feedback is None:
        feedback = AISuggestionFeedback(suggestion_id=suggestion_id, customer_id=customer_id, target_type=target_type, target_id=target_id, actor_user_id=actor.id, action=action, edited_content=edited_content)
        feedback_dao.add(db, feedback)
    else:
        feedback.actor_user_id = actor.id
        feedback.suggestion_id = suggestion_id or feedback.suggestion_id
        feedback.action = action
        feedback.edited_content = edited_content
    logger.info(
        "ai_suggestion_feedback",
        extra={
            "event": "ai_suggestion_feedback",
            "customer_id": customer_id,
            "provider_name": "human_feedback",
            "run_id": None,
        },
    )
    return feedback


def record_feedback(db: Session, suggestion: AISuggestion, actor: User, action: str, edited_content: dict | None = None) -> AISuggestionFeedback:
    """兼容 reply/schedule 的旧调用，并把建议类型作为反馈目标。"""
    return record_target_feedback(db, suggestion.customer_id, actor, suggestion.suggestion_type, str(suggestion.id), action, edited_content, suggestion.id)


def record_agent_feedback(
    db: Session,
    customer_id: int,
    run_id: int,
    actor: User,
    action: str,
    note: str | None = None,
) -> AISuggestionFeedback:
    """记录综合 Agent 的人工纠错，采用 run_id 幂等，避免重复统计。"""

    if action not in ALLOWED_AGENT_ACTIONS:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Agent 反馈操作无效")
    get_customer_or_404(db, customer_id, actor, "read")
    run = workflow_run_dao.get_by_id(db, customer_id, run_id)
    if run is None or run.goal != "agent_comprehensive":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="综合 Agent 运行不存在")
    if run.status not in {"waiting_human", "failed"}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="当前 Agent 运行还不能提交反馈")
    result = run.result_json if isinstance(run.result_json, dict) else {}
    suggestion_ids = result.get("suggestion_ids", [])
    suggestion_id = next((int(value) for value in suggestion_ids if isinstance(value, int)), None) if isinstance(suggestion_ids, list) else None
    target_type, target_id = "agent_run", str(run_id)
    feedback = feedback_dao.get_by_target(db, target_type, target_id)
    if feedback is None:
        feedback = AISuggestionFeedback(
            suggestion_id=suggestion_id,
            customer_id=customer_id,
            target_type=target_type,
            target_id=target_id,
            actor_user_id=actor.id,
            action=action,
            note=(note or "").strip()[:300] or None,
        )
        feedback_dao.add(db, feedback)
    else:
        feedback.actor_user_id = actor.id
        feedback.suggestion_id = suggestion_id or feedback.suggestion_id
        feedback.action = action
        feedback.note = (note or "").strip()[:300] or None
    append_audit_log(
        db,
        actor,
        "customer.agent_reasoning_feedback",
        "agent_run",
        str(run_id),
        {"customer_id": customer_id, "action": action},
    )
    from app.services.rag_evaluation_service import create_case_from_agent_feedback

    create_case_from_agent_feedback(db, run, actor)
    logger.info(
        "agent_reasoning_feedback",
        extra={"event": "agent_reasoning_feedback", "run_id": run_id, "customer_id": customer_id},
    )
    return feedback
