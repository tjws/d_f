"""销售执行中心：统一显示 AI 审阅事项与已确认跟进日程。"""

from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.dao.my_work_dao import MyWorkDAO
from app.models.user import User
from app.services.customer_service import customer_scope_filters
from app.services.pending_action_service import list_pending_actions


my_work_dao = MyWorkDAO()
_DISPLAY_TIMEZONE = ZoneInfo("Asia/Shanghai")
_BUCKET_ORDER = {"overdue": 0, "today": 1, "upcoming": 2, "review": 3, "historical": 4}
_HISTORICAL_REVIEW_AFTER = timedelta(days=7)


def _time_window(now: datetime) -> tuple[datetime, datetime]:
    """按中国本地日历计算今日边界，但数据库查询和比较仍使用 UTC。"""

    local_now = now.astimezone(_DISPLAY_TIMEZONE)
    today_start_local = datetime.combine(local_now.date(), time.min, tzinfo=_DISPLAY_TIMEZONE)
    tomorrow_start_local = today_start_local + timedelta(days=1)
    return today_start_local.astimezone(timezone.utc), tomorrow_start_local.astimezone(timezone.utc)


def _schedule_bucket(due_at: datetime, now: datetime, today_end: datetime) -> str:
    due_utc = due_at if due_at.tzinfo is not None else due_at.replace(tzinfo=timezone.utc)
    if due_utc < now:
        return "overdue"
    if due_utc < today_end:
        return "today"
    return "upcoming"


def get_my_work(
    db: Session,
    current_user: User,
    bucket: str | None = None,
    limit: int = 100,
    now: datetime | None = None,
) -> dict[str, object]:
    """按用户客户数据范围聚合工作事项；该接口不改变任何业务状态。"""

    current = now or datetime.now(timezone.utc)
    current = current if current.tzinfo is not None else current.replace(tzinfo=timezone.utc)
    _, today_end = _time_window(current)
    customer_filters = customer_scope_filters(db, current_user, "read")
    items: list[dict[str, object]] = []

    # 复用待处理建议服务，确保画像、回复、标签、日程草稿与独立工作台一致。
    pending_actions = list_pending_actions(db, current_user, limit=limit)
    historical_before = current.astimezone(_DISPLAY_TIMEZONE).date() - _HISTORICAL_REVIEW_AFTER
    for action in pending_actions:
        # 按销售看到的自然日归类：七天前当天生成的草稿也进入历史，
        # 不能因生成时刻相差几小时继续占据“今日”的注意力。
        action_created_at = action["created_at"]
        if action_created_at.tzinfo is None:
            action_created_at = action_created_at.replace(tzinfo=timezone.utc)
        review_bucket = "historical" if action_created_at.astimezone(_DISPLAY_TIMEZONE).date() <= historical_before else "review"
        items.append(
            {
                "id": f"review:{action['id']}",
                "resource_id": action["resource_id"],
                "item_type": "ai_review",
                "bucket": review_bucket,
                "action_type": action["action_type"],
                "status": action["status"],
                "customer_id": action["customer_id"],
                "customer_name": action["customer_name"],
                "customer_stage": action["customer_stage"],
                "title": action["title"],
                "summary": action["summary"],
                "priority": None,
                "due_at": None,
                "created_at": action["created_at"],
            }
        )

    for schedule, customer_name, customer_stage in my_work_dao.list_open_schedules(
        db, current_user.id, customer_filters
    ):
        schedule_bucket = _schedule_bucket(schedule.due_at, current, today_end)
        items.append(
            {
                "id": f"schedule:{schedule.id}",
                "resource_id": schedule.id,
                "item_type": "schedule",
                "bucket": schedule_bucket,
                "action_type": None,
                "status": schedule.status,
                "customer_id": schedule.customer_id,
                "customer_name": customer_name,
                "customer_stage": customer_stage,
                "title": schedule.title,
                "summary": (schedule.description or "已确认跟进日程，请在完成后标记完成。")[:120],
                "priority": schedule.priority,
                "due_at": schedule.due_at,
                "created_at": schedule.created_at,
            }
        )

    summary = {name: sum(item["bucket"] == name for item in items) for name in _BUCKET_ORDER}
    if bucket is not None:
        items = [item for item in items if item["bucket"] == bucket]
    items.sort(
        key=lambda item: (
            _BUCKET_ORDER[str(item["bucket"])],
            item["due_at"] or item["created_at"],
        )
    )
    return {"summary": summary, "items": items[:limit]}
