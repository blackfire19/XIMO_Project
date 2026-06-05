from datetime import date, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.constants import FREQ_DAYS
from app.core.deps import get_current_user, require_roles
from app.database import get_db
from app.models.customer import Customer, FollowUpRecord
from app.models.inquiry import FormalOrder, ShipmentBL
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

    today_records = (
        db.query(FollowUpRecord)
        .filter(func.substr(FollowUpRecord.created_at, 1, 10) == today)
        .all()
    )
    total_follow_count = len({r.customer_id for r in today_records})
    effective_follow_count = sum(1 for r in today_records if r.is_effective)

    effective_records = sorted(
        [r for r in today_records if r.is_effective],
        key=lambda r: r.created_at,
        reverse=True,
    )
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

    active_orders = (
        db.query(FormalOrder)
        .filter(FormalOrder.status != "completed")
        .order_by(FormalOrder.created_at.desc())
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
            "est_ready_date": str(o.est_production_date) if o.est_production_date else None,
            "created_at": str(o.created_at),
        }
        for o in active_orders
    ]

    # 本月出运计划：关联提单 ETD 在本月的待出运/出运中订单
    month_prefix = today[:7]
    shipment_orders = (
        db.query(FormalOrder)
        .join(ShipmentBL, ShipmentBL.order_id == FormalOrder.id)
        .filter(
            FormalOrder.status.in_(["ready", "shipping"]),
            func.substr(ShipmentBL.etd, 1, 7) == month_prefix,
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

    status_counts = dict(
        db.query(FormalOrder.status, func.count(FormalOrder.id))
        .group_by(FormalOrder.status)
        .all()
    )

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

    my_customers = (
        db.query(Customer)
        .filter(Customer.owner_id == current_user.id, Customer.is_active == True)
        .all()
    )

    customer_ids = [c.id for c in my_customers]
    last_followup_map: dict[int, date] = {}
    if customer_ids:
        rows = (
            db.query(
                FollowUpRecord.customer_id,
                func.max(FollowUpRecord.created_at).label("last_at"),
            )
            .filter(FollowUpRecord.customer_id.in_(customer_ids))
            .group_by(FollowUpRecord.customer_id)
            .all()
        )
        for cid, last_at in rows:
            last_followup_map[cid] = date.fromisoformat(str(last_at)[:10])

    today_date = date.fromisoformat(today)
    due_today = []
    today_follow_count = 0
    for c in my_customers:
        threshold = FREQ_DAYS.get(c.follow_freq, 1)
        last = last_followup_map.get(c.id)
        if last == today_date:
            today_follow_count += 1
        days_since = (today_date - last).days if last else threshold
        if days_since >= threshold:
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

    my_active_orders = (
        db.query(FormalOrder)
        .filter(
            FormalOrder.salesperson_id == current_user.id,
            FormalOrder.status != "completed",
        )
        .order_by(FormalOrder.created_at.desc())
        .all()
    )
    active_orders = [
        {
            "id": o.id,
            "so_number": o.so_number,
            "customer_id": o.customer_id,
            "status": o.status,
            "est_ready_date": str(o.est_production_date) if o.est_production_date else None,
            "created_at": str(o.created_at),
        }
        for o in my_active_orders
    ]

    return {
        "my_customer_count": len(my_customers),
        "due_today_customers": due_today,
        "today_follow_count": today_follow_count,
        "active_orders": active_orders,
    }
