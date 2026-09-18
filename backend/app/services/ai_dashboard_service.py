from datetime import datetime, timedelta, timezone
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.dao.ai_dashboard_dao import AIDashboardDAO

dashboard_dao = AIDashboardDAO()


def get_ai_dashboard(db: Session, start: datetime | None, end: datetime | None) -> dict[str, object]:
    now = datetime.now(timezone.utc)
    end_at = end or now
    start_at = start or (end_at - timedelta(days=7))
    if end_at <= start_at or (end_at - start_at).days > 31:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="时间范围必须为 0 到 31 天")
    suggestions = dashboard_dao.suggestions(db, start_at, end_at)
    profiles = dashboard_dao.profiles(db, start_at, end_at)
    ai_tags = dashboard_dao.ai_tags(db, start_at, end_at)
    feedback = dashboard_dao.feedback(db, start_at, end_at)
    runs = dashboard_dao.workflow_runs(db, start_at, end_at)
    rag_interactions = dashboard_dao.rag_interactions(db, start_at, end_at)
    counts = {"accepted": 0, "edited": 0, "rejected": 0}
    for item in feedback:
        if item.action in counts:
            counts[item.action] += 1
    by_type = {kind: {"suggestions": 0, "accepted": 0, "edited": 0, "rejected": 0} for kind in ("profile", "reply", "tag", "schedule")}
    for item in suggestions:
        by_type.setdefault(item.suggestion_type, {"suggestions": 0, "accepted": 0, "edited": 0, "rejected": 0})["suggestions"] += 1
    by_type["profile"]["suggestions"] += len(profiles)
    by_type["tag"]["suggestions"] += len(ai_tags)
    suggestions_by_id = {item.id: item for item in suggestions}
    for item in feedback:
        feedback_type = item.target_type if item.target_type in by_type else None
        if feedback_type is None and item.suggestion_id is not None:
            suggestion = suggestions_by_id.get(item.suggestion_id)
            feedback_type = suggestion.suggestion_type if suggestion is not None else None
        if feedback_type is not None and item.action in counts:
            by_type[feedback_type][item.action] += 1
    workflow = {"succeeded": 0, "failed": 0, "waiting_human": 0}
    bailian_calls = bailian_failures = 0
    for run in runs:
        # Agent 规划是一次受控的模型调用，但不是“生成建议工作流”；
        # 它计入成本统计，不能把工作流成功率虚高。
        if run.goal != "agent_plan":
            if run.status == "failed":
                workflow["failed"] += 1
            elif (run.result_json or {}).get("status") == "waiting_human":
                workflow["waiting_human"] += 1
            elif run.status == "succeeded":
                workflow["succeeded"] += 1
        if run.provider_name == "bailian":
            bailian_calls += 1
            bailian_failures += int(run.status == "failed")
    total_feedback = len(feedback)
    agent_feedback = [item for item in feedback if item.target_type == "agent_run"]
    agent_feedback_by_action = {"incorrect_reasoning": 0, "missing_information": 0, "not_useful": 0}
    for item in agent_feedback:
        if item.action in agent_feedback_by_action:
            agent_feedback_by_action[item.action] += 1
    agent_runs = [item for item in runs if item.goal == "agent_comprehensive"]
    reasoning_failures = sum(
        item.status == "failed" or (item.result_json or {}).get("reasoning_status") == "failed"
        for item in agent_runs
    )
    durations = [
        max(0, int((item.finished_at - item.started_at).total_seconds() * 1000))
        for item in agent_runs
        if item.started_at is not None and item.finished_at is not None
    ]
    rag_queries = [item for item in rag_interactions if item.query_excerpt]
    rag_fallbacks = sum(bool(item.fallback) for item in rag_queries)
    return {
        "start": start_at,
        "end": end_at,
        "suggestions_total": len(suggestions) + len(profiles) + len(ai_tags),
        "feedback_total": total_feedback,
        "accepted": counts["accepted"],
        "edited": counts["edited"],
        "rejected": counts["rejected"],
        "adoption_rate": (counts["accepted"] + counts["edited"]) / total_feedback if total_feedback else 0,
        "by_suggestion_type": by_type,
        "workflow": workflow,
        "bailian_calls": bailian_calls,
        "bailian_failures": bailian_failures,
        "rag_queries_total": len(rag_queries),
        "rag_fallbacks": rag_fallbacks,
        "rag_fallback_rate": rag_fallbacks / len(rag_queries) if rag_queries else 0,
        "agent_feedback_total": len(agent_feedback),
        "agent_feedback_by_action": agent_feedback_by_action,
        "agent_reasoning_total": len(agent_runs),
        "agent_reasoning_failures": reasoning_failures,
        "agent_reasoning_failure_rate": reasoning_failures / len(agent_runs) if agent_runs else 0,
        "avg_task_duration_ms": round(sum(durations) / len(durations)) if durations else 0,
    }
