"""AI 灰度名单、功能门禁和每日指标快照。"""

from datetime import date, datetime, time, timedelta, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.dao.ai_rollout_dao import AIRolloutDAO
from app.dao.system_setting_dao import SystemSettingDAO
from app.models.ai_rollout_daily_report import AIRolloutDailyReport
from app.models.ai_rollout_membership import AIRolloutMembership
from app.models.user import User
from app.schemas.ai_rollout import AIRolloutMemberCreate
from app.services.ai_dashboard_service import get_ai_dashboard
from app.services.audit_log_service import append_audit_log


MAX_PILOT_MEMBERS = 30
rollout_dao = AIRolloutDAO()
setting_dao = SystemSettingDAO()


def rollout_mode(db: Session) -> str:
    value = setting_dao.get_global(db, "ai_rollout_mode")
    return str(value.value_json).strip().lower() if value is not None else "all"


def is_rollout_allowed(db: Session, user_id: int) -> bool:
    """全量模式放行；pilot 模式只放行 active 灰度成员。"""

    if rollout_mode(db) != "pilot":
        return True
    membership = rollout_dao.get_membership(db, user_id)
    return membership is not None and membership.status == "active"


def require_rollout_access(db: Session, user: User, feature_name: str) -> None:
    if not is_rollout_allowed(db, user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"{feature_name} 当前处于灰度阶段，该账号未加入灰度名单",
        )


def config_read(db: Session) -> dict[str, object]:
    return {
        "mode": rollout_mode(db),
        "active_member_count": len(rollout_dao.active_memberships(db)),
        "max_member_count": MAX_PILOT_MEMBERS,
    }


def set_mode(db: Session, actor: User, mode: str) -> dict[str, object]:
    if mode not in {"all", "pilot"}:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="灰度模式只能是 all 或 pilot")
    setting = setting_dao.get_global(db, "ai_rollout_mode")
    if setting is None:
        from app.models.system_setting import SystemSetting

        setting = SystemSetting(
            key="ai_rollout_mode",
            value_json=mode,
            scope_type="global",
            description="AI 综合 Agent 灰度模式：all 全量，pilot 仅灰度名单。",
            updated_by=actor.id,
        )
        setting_dao.add(db, setting)
    else:
        setting.value_json = mode
        setting.updated_by = actor.id
    append_audit_log(db, actor, "ai_rollout.mode_changed", "system_setting", "ai_rollout_mode", {"mode": mode})
    db.commit()
    return config_read(db)


def _member_read(membership: AIRolloutMembership, user: User) -> dict[str, object]:
    return {
        "id": membership.id,
        "user_id": user.id,
        "username": user.username,
        "full_name": user.full_name,
        "role": user.role,
        "segment": membership.segment,
        "status": membership.status,
        "added_by": membership.added_by,
        "started_at": membership.started_at,
        "ended_at": membership.ended_at,
        "created_at": membership.created_at,
    }


def list_members(db: Session) -> list[dict[str, object]]:
    users = {user.id: user for user in db.query(User).all()}
    return [_member_read(item, users[item.user_id]) for item in rollout_dao.list_memberships(db) if item.user_id in users]


def add_member(db: Session, actor: User, payload: AIRolloutMemberCreate) -> dict[str, object]:
    user = db.get(User, payload.user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="灰度用户不存在或已停用")
    existing = rollout_dao.get_membership(db, user.id)
    active_count = len(rollout_dao.active_memberships(db))
    if existing is not None and existing.status == "active":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="该用户已在灰度名单中")
    if existing is None and active_count >= MAX_PILOT_MEMBERS:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="灰度名单最多允许 30 名 active 用户")
    now = datetime.now(timezone.utc)
    if existing is None:
        membership = AIRolloutMembership(user_id=user.id, segment=payload.segment, status="active", added_by=actor.id, started_at=now)
        rollout_dao.add_membership(db, membership)
    else:
        existing.segment = payload.segment
        existing.status = "active"
        existing.added_by = actor.id
        existing.started_at = now
        existing.ended_at = None
        membership = existing
    append_audit_log(db, actor, "ai_rollout.member_added", "user", str(user.id), {"segment": payload.segment})
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="该用户已存在灰度记录") from None
    db.refresh(membership)
    return _member_read(membership, user)


def remove_member(db: Session, actor: User, user_id: int) -> None:
    membership = rollout_dao.get_membership(db, user_id)
    if membership is None or membership.status != "active":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="active 灰度成员不存在")
    membership.status = "removed"
    membership.ended_at = datetime.now(timezone.utc)
    append_audit_log(db, actor, "ai_rollout.member_removed", "user", str(user_id), {})
    db.commit()


def _report_read(report: AIRolloutDailyReport) -> dict[str, object]:
    return {
        "id": report.id,
        "report_date": report.report_date,
        "cohort": report.cohort,
        "metrics": report.metrics_json,
        "generated_by": report.generated_by,
        "created_at": report.created_at,
        "updated_at": report.updated_at,
    }


def generate_daily_report(db: Session, actor: User, report_date: date | None = None) -> dict[str, object]:
    day = report_date or datetime.now(timezone.utc).date()
    start = datetime.combine(day, time.min, tzinfo=timezone.utc)
    end = start + timedelta(days=1)
    dashboard = get_ai_dashboard(db, start, end)
    metrics: dict[str, Any] = dict(dashboard)
    metrics["start"] = start.isoformat()
    metrics["end"] = end.isoformat()
    metrics["active_member_count"] = len(rollout_dao.active_memberships(db))
    metrics["rollout_mode"] = rollout_mode(db)
    report = rollout_dao.get_report(db, day, "pilot")
    if report is None:
        report = AIRolloutDailyReport(report_date=day, cohort="pilot", metrics_json=metrics, generated_by=actor.id)
        rollout_dao.add_report(db, report)
    else:
        report.metrics_json = metrics
        report.generated_by = actor.id
    append_audit_log(db, actor, "ai_rollout.daily_report_generated", "ai_rollout_daily_report", day.isoformat(), {"cohort": "pilot"})
    db.commit()
    db.refresh(report)
    return _report_read(report)


def list_reports(db: Session, limit: int = 30) -> list[dict[str, object]]:
    return [_report_read(item) for item in rollout_dao.list_reports(db, max(1, min(limit, 90)))]


__all__ = [
    "MAX_PILOT_MEMBERS",
    "add_member",
    "config_read",
    "generate_daily_report",
    "is_rollout_allowed",
    "list_members",
    "list_reports",
    "remove_member",
    "require_rollout_access",
    "rollout_mode",
    "set_mode",
]

