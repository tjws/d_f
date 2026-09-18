from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.dao.business_dashboard_dao import BusinessDashboardDAO


dashboard_dao = BusinessDashboardDAO()
PAID_STATUSES = {"paid", "completed"}
FUNNEL_STAGES = ("new", "following_up", "converted", "lost")


def _window(start: datetime | None, end: datetime | None) -> tuple[datetime, datetime]:
    end_at = end or datetime.now(timezone.utc)
    start_at = start or (end_at - timedelta(days=7))
    if end_at <= start_at or (end_at - start_at).days > 31:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="时间范围必须为 0 到 31 天")
    return start_at, end_at


def get_business_dashboard(db: Session, start: datetime | None, end: datetime | None) -> dict[str, object]:
    """汇总经营事实；续费率使用可解释的“重复付费客户比例”代理定义。"""

    start_at, end_at = _window(start, end)
    customers = dashboard_dao.customers_in_window(db, start_at, end_at)
    all_customers = {item.id: item for item in dashboard_dao.all_customers(db)}
    orders = dashboard_dao.orders_in_window(db, start_at, end_at)
    tickets = dashboard_dao.tickets_in_window(db, start_at, end_at)

    funnel_counts = Counter(item.stage for item in customers)
    funnel = [{"stage": stage, "count": funnel_counts.get(stage, 0)} for stage in FUNNEL_STAGES]

    order_status_counts = Counter(item.status for item in orders)
    paid_orders = [item for item in orders if item.status in PAID_STATUSES]
    paying_customers = Counter(item.customer_id for item in paid_orders)
    repeat_count = sum(count >= 2 for count in paying_customers.values())
    paid_amount = sum(float(item.amount or 0) for item in paid_orders)

    ticket_status_counts = Counter(item.status for item in tickets)
    open_ticket_count = sum(ticket.status in {"open", "in_progress"} for ticket in tickets)

    customer_by_owner: dict[int, list] = defaultdict(list)
    for customer in customers:
        if customer.owner_id is not None:
            customer_by_owner[customer.owner_id].append(customer)
    paid_amount_by_owner: Counter[int] = Counter()
    for order in paid_orders:
        customer = all_customers.get(order.customer_id)
        if customer and customer.owner_id is not None:
            paid_amount_by_owner[customer.owner_id] += float(order.amount or 0)
    open_tickets_by_owner: Counter[int] = Counter()
    for ticket in tickets:
        if ticket.status not in {"open", "in_progress"}:
            continue
        customer = all_customers.get(ticket.customer_id)
        if customer and customer.owner_id is not None:
            open_tickets_by_owner[customer.owner_id] += 1

    owner_efficiency = []
    for user in dashboard_dao.active_sales_users(db):
        owned = customer_by_owner.get(user.id, [])
        owner_efficiency.append(
            {
                "user_id": user.id,
                "username": user.username,
                "full_name": user.full_name,
                "customer_count": len(owned),
                "converted_customer_count": sum(item.stage == "converted" for item in owned),
                "paid_amount": round(paid_amount_by_owner[user.id], 2),
                "open_ticket_count": open_tickets_by_owner[user.id],
            }
        )
    owner_efficiency.sort(key=lambda item: (-item["converted_customer_count"], -item["paid_amount"], item["username"]))

    return {
        "start": start_at,
        "end": end_at,
        "customer_total": len(customers),
        "funnel": funnel,
        "orders": {
            "total": len(orders),
            "by_status": dict(order_status_counts),
            "paid_or_completed": len(paid_orders),
            "paid_amount": round(paid_amount, 2),
        },
        "tickets": {
            "total": len(tickets),
            "by_status": dict(ticket_status_counts),
            "open_count": open_ticket_count,
        },
        "paying_customer_count": len(paying_customers),
        "repeat_purchase_customer_count": repeat_count,
        "renewal_rate": repeat_count / len(paying_customers) if paying_customers else 0,
        "renewal_rate_definition": "重复付费客户数 / 至少有一笔 paid 或 completed 订单的客户数；当前作为续费率的 MVP 代理指标。",
        "owner_efficiency": owner_efficiency,
    }
