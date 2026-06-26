import ipaddress
from datetime import date, timedelta
from calendar import monthrange
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import distinct, func
from sqlalchemy.orm import Session

from app.core.constants import FREQ_DAYS
from app.core.deps import get_current_user, require_roles
from app.database import get_db
from app.models.accounting import AccountingRecord
from app.models.customer import Customer, FollowUpRecord
from app.models.inquiry import FormalOrder, OrderFile, ShipmentBL
from app.models.user import User

router = APIRouter(prefix="/dashboard", tags=["首页看板"])

# 国内（本国）国家名的各种历史写法，海外客户热力图需全部排除
DOMESTIC_COUNTRY_NAMES = ("China", "中国", "中華人民共和国", "中华人民共和国", "中國")


def _today_str() -> str:
    return date.today().isoformat()


def require_lan(request: Request):
    """大屏公开接口：仅允许内网/本机访问，避免聚合经营数据被公网抓取。
    注意：若经反向代理，request.client.host 可能是代理 IP；此时需在代理层（如 Nginx allow/deny）
    另行限制，或确保代理转发真实客户端 IP。"""
    host = request.client.host if request.client else ""
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        raise HTTPException(status_code=403, detail="仅限内网访问")
    # 双栈环境下局域网客户端可能以 IPv4-mapped IPv6（::ffff:192.168.x.x）出现，先还原为 IPv4 再判断
    if getattr(ip, "ipv4_mapped", None) is not None:
        ip = ip.ipv4_mapped
    if not (ip.is_private or ip.is_loopback or ip.is_link_local):
        raise HTTPException(status_code=403, detail="仅限内网访问")


@router.get("/world-map")
def world_map(db: Session = Depends(get_db), _: None = Depends(require_lan)):
    """公开只读（仅内网）：用于局域网 TV 大屏展示。仅返回按国家聚合的数字，不含任何敏感信息。"""
    # 航线：未完结订单按提单目的国去重计订单数
    route_rows = (
        db.query(
            ShipmentBL.discharge_country,
            func.count(distinct(FormalOrder.id)),
        )
        .join(FormalOrder, ShipmentBL.order_id == FormalOrder.id)
        .filter(
            FormalOrder.status != "completed",
            ShipmentBL.discharge_country.isnot(None),
            ShipmentBL.discharge_country != "",
        )
        .group_by(ShipmentBL.discharge_country)
        .all()
    )
    routes = [
        {"country": country, "order_count": count}
        for country, count in route_rows
    ]

    # 热力：在册海外客户（排除中国）按所在国计数
    customer_rows = (
        db.query(Customer.country, func.count(Customer.id))
        .filter(
            Customer.is_active == True,
            Customer.country.isnot(None),
            Customer.country != "",
            Customer.country.notin_(DOMESTIC_COUNTRY_NAMES),
        )
        .group_by(Customer.country)
        .all()
    )
    customers = [
        {"country": country, "count": count}
        for country, count in customer_rows
    ]

    return {"routes": routes, "customers": customers}


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
    customers_map = {c.id: c for c in db.query(Customer).filter(Customer.id.in_(customer_ids)).all()} if customer_ids else {}
    follow_summary = [
        {
            "id": r.id,
            "customer_id": r.customer_id,
            "customer_name": customers_map[r.customer_id].company_name if r.customer_id in customers_map else f"客户 #{r.customer_id}",
            "contact_name": customers_map[r.customer_id].contact_name if r.customer_id in customers_map else None,
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
    today_date = date.fromisoformat(today)
    month_start = today_date.replace(day=1)
    month_end = today_date.replace(day=monthrange(today_date.year, today_date.month)[1])
    shipment_orders = (
        db.query(FormalOrder)
        .join(ShipmentBL, ShipmentBL.order_id == FormalOrder.id)
        .filter(
            FormalOrder.status.in_(["ready", "shipping"]),
            ShipmentBL.etd >= month_start,
            ShipmentBL.etd <= month_end,
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


@router.get("/finance")
def finance_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("finance", "super_admin")),
):
    all_records = db.query(AccountingRecord).all()
    accounted_order_ids = {r.order_id for r in all_records}
    salary_pending_ids = {r.order_id for r in all_records if not r.salary_calculated}

    completed_orders = (
        db.query(FormalOrder)
        .filter(FormalOrder.status == "completed")
        .order_by(FormalOrder.updated_at.desc())
        .all()
    )
    pending_accounting = [o for o in completed_orders if o.id not in accounted_order_ids]
    accounted = [o for o in completed_orders if o.id in accounted_order_ids]

    # 待发放工资：已记账但 salary_calculated=False，按记账时间排序
    record_map = {r.order_id: r for r in all_records}
    salary_pending_orders = sorted(
        [o for o in completed_orders if o.id in salary_pending_ids],
        key=lambda o: record_map[o.id].recorded_at,
        reverse=True,
    )

    def _order_brief(o: FormalOrder, with_recorded_at: bool = False) -> dict:
        d = {
            "id": o.id,
            "so_number": o.so_number,
            "customer_id": o.customer_id,
            "updated_at": str(o.updated_at),
        }
        if with_recorded_at and o.id in record_map:
            d["recorded_at"] = str(record_map[o.id].recorded_at)
            d["profit"] = float(record_map[o.id].profit) if record_map[o.id].profit is not None else None
        return d

    return {
        "pending_accounting_count": len(pending_accounting),
        "accounted_count": len(accounted),
        "salary_pending_count": len(salary_pending_orders),
        "pending_orders": [_order_brief(o) for o in pending_accounting[:5]],
        "salary_pending_orders": [_order_brief(o, with_recorded_at=True) for o in salary_pending_orders[:5]],
    }


# 后勤需补传的出运单据类型（由后勤上传）
LOGISTICS_REQUIRED_DOCS = ["export_permit", "co"]
LOGISTICS_DOC_LABELS = {"export_permit": "出口许可证", "co": "CO 原产地证"}


@router.get("/logistics")
def logistics_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("logistics", "super_admin")),
):
    """后勤看板：所有仍缺「出口许可证」或「CO 原产地证」的订单都需后勤补传（不按合同状态过滤）。"""
    orders = (
        db.query(FormalOrder)
        .order_by(FormalOrder.updated_at.desc())
        .all()
    )
    order_ids = [o.id for o in orders]

    have_map: dict[int, set[str]] = {}
    if order_ids:
        rows = (
            db.query(OrderFile.order_id, OrderFile.doc_type)
            .filter(
                OrderFile.order_id.in_(order_ids),
                OrderFile.doc_type.in_(LOGISTICS_REQUIRED_DOCS),
            )
            .distinct()
            .all()
        )
        for oid, dt in rows:
            have_map.setdefault(oid, set()).add(dt)

    pending = []
    for o in orders:
        have = have_map.get(o.id, set())
        missing = [d for d in LOGISTICS_REQUIRED_DOCS if d not in have]
        if missing:
            pending.append(
                {
                    "id": o.id,
                    "so_number": o.so_number,
                    "status": o.status,
                    "customer_id": o.customer_id,
                    "customer_name": o.customer.company_name if o.customer else None,
                    "contact_name": o.customer.contact_name if o.customer else None,
                    "missing": missing,
                    "missing_labels": [LOGISTICS_DOC_LABELS[d] for d in missing],
                    "updated_at": str(o.updated_at),
                }
            )

    return {
        "pending_docs_count": len(pending),
        "pending_docs_orders": pending,
    }
