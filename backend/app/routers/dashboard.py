from datetime import date, datetime
from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_roles
from app.database import get_db
from app.models.customer import Customer, FollowUpRecord
from app.models.order import Order
from app.models.user import User

router = APIRouter(prefix="/dashboard", tags=["首页看板"])


def _today_str() -> str:
    return date.today().isoformat()


@router.get("/boss")
def boss_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("boss", "super_admin")),
):
    today = _today_str()

    # 今日全员跟进数（有跟进记录的客户数，去重）& 今日有效跟进条数
    today_records = (
        db.query(FollowUpRecord)
        .filter(func.substr(FollowUpRecord.created_at, 1, 10) == today)
        .all()
    )
    total_follow_count = len({r.customer_id for r in today_records})
    effective_follow_count = sum(1 for r in today_records if r.is_effective)

    # 今日有效跟进摘要（全部，按时间倒序）
    effective_records = sorted(
        [r for r in today_records if r.is_effective],
        key=lambda r: r.created_at,
        reverse=True,
    )
    # 预加载创建人和客户信息
    creator_ids = {r.created_by for r in effective_records}
    customer_ids = {r.customer_id for r in effective_records}
    creators = {u.id: u.full_name for u in db.query(User).filter(User.id.in_(creator_ids)).all()} if creator_ids else {}
    customers_map = {c.id: c.company_name for c in db.query(Customer).filter(Customer.id.in_(customer_ids)).all()} if customer_ids else {}
    follow_summary = [
        {
            "id": r.id,
            "customer_id": r.customer_id,
            "customer_name": customers_map.get(r.customer_id, f"客户 #{r.customer_id}"),
            "content": r.content,
            "created_by": r.created_by,
            "creator_name": creators.get(r.created_by, ""),
            "created_at": r.created_at,
        }
        for r in effective_records
    ]

    # 进行中订单总览（非已完结）
    active_orders = (
        db.query(Order)
        .filter(Order.status != "completed")
        .order_by(Order.created_at.desc())
        .limit(20)
        .all()
    )
    orders_overview = [
        {
            "id": o.id,
            "so_number": o.so_number,
            "customer_id": o.customer_id,
            "status": o.status,
            "salesperson_id": o.salesperson_id,
            "est_ready_date": str(o.est_ready_date) if o.est_ready_date else None,
            "created_at": str(o.created_at),
        }
        for o in active_orders
    ]

    # 本月出运计划（待出运 + 已出运，当月创建）
    month_prefix = today[:7]
    shipment_orders = (
        db.query(Order)
        .filter(
            Order.status.in_(["pending_shipment", "shipped"]),
            func.substr(Order.created_at, 1, 7) == month_prefix,
        )
        .all()
    )
    shipment_plan = [
        {
            "id": o.id,
            "so_number": o.so_number,
            "customer_id": o.customer_id,
            "status": o.status,
        }
        for o in shipment_orders
    ]

    # 各状态订单统计
    status_counts = {}
    for o in db.query(Order).all():
        status_counts[o.status] = status_counts.get(o.status, 0) + 1

    return {
        "today_follow_count": total_follow_count,
        "today_effective_follow_count": effective_follow_count,
        "follow_summary": follow_summary,
        "active_orders": orders_overview,
        "shipment_plan": shipment_plan,
        "order_status_counts": status_counts,
    }


@router.get("/salesperson")
def salesperson_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("salesperson", "super_admin")),
):
    today = _today_str()

    # 今日应跟进客户（属于我的客户，follow_freq 对应今天需要跟进的）
    my_customers = (
        db.query(Customer)
        .filter(Customer.owner_id == current_user.id, Customer.is_active == True)
        .all()
    )

    # 判断客户今日是否已有跟进记录
    today_followed_ids = {
        r.customer_id
        for r in db.query(FollowUpRecord)
        .filter(
            FollowUpRecord.created_by == current_user.id,
            func.substr(FollowUpRecord.created_at, 1, 10) == today,
        )
        .all()
    }

    due_today = []
    for c in my_customers:
        if c.id not in today_followed_ids:
            due_today.append(
                {
                    "id": c.id,
                    "company_name": c.company_name,
                    "country": c.country,
                    "contact_name": c.contact_name,
                    "grade": c.grade,
                    "follow_freq": c.follow_freq,
                }
            )

    # 我的进行中订单
    my_active_orders = (
        db.query(Order)
        .filter(
            Order.salesperson_id == current_user.id,
            Order.status != "completed",
        )
        .order_by(Order.created_at.desc())
        .all()
    )
    active_orders = [
        {
            "id": o.id,
            "so_number": o.so_number,
            "customer_id": o.customer_id,
            "status": o.status,
            "est_ready_date": str(o.est_ready_date) if o.est_ready_date else None,
            "created_at": str(o.created_at),
        }
        for o in my_active_orders
    ]

    # 我的客户总数 & 今日跟进数
    my_today_records = db.query(FollowUpRecord).filter(
        FollowUpRecord.created_by == current_user.id,
        func.substr(FollowUpRecord.created_at, 1, 10) == today,
    ).count()

    return {
        "my_customer_count": len(my_customers),
        "due_today_customers": due_today,
        "today_follow_count": my_today_records,
        "active_orders": active_orders,
    }
