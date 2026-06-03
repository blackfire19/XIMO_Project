import os
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session, aliased

from app.config import settings
from app.core.deps import get_current_user, require_roles
from app.database import get_db
from app.models.customer import Customer, FollowUpImage, FollowUpRecord
from app.models.user import User
from app.schemas.customer import (
    CustomerCreate,
    CustomerOut,
    CustomerUpdate,
    FollowUpOut,
    FreqUpgradeBody,
)

router = APIRouter(prefix="/customers", tags=["客户管理"])

FREQ_ORDER = ["daily", "weekly", "monthly"]
CYCLE_DAYS = {"daily": 1, "weekly": 7, "monthly": 30}


def _parse_dt(val) -> datetime:
    if isinstance(val, datetime):
        return val
    s = str(val)
    for fmt in (
        "%Y-%m-%d %H:%M:%S.%f%z",
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
    ):
        try:
            return datetime.strptime(s[:26], fmt.replace("%z", ""))
        except ValueError:
            continue
    return datetime.utcnow()


def _check_downgrade(customer: Customer, db: Session) -> None:
    """Downgrade follow_freq if 3+ consecutive cycles have no effective record."""
    if customer.follow_freq == "monthly":
        return

    now = datetime.utcnow()
    cycle_days = CYCLE_DAYS[customer.follow_freq]

    last_effective = (
        db.query(FollowUpRecord)
        .filter(
            FollowUpRecord.customer_id == customer.id,
            FollowUpRecord.is_effective == True,  # noqa: E712
        )
        .order_by(FollowUpRecord.created_at.desc())
        .first()
    )

    last_change_dt = _parse_dt(customer.follow_freq_updated_at)

    if last_effective:
        effective_dt = _parse_dt(last_effective.created_at)
        baseline = max(effective_dt, last_change_dt)
    else:
        baseline = last_change_dt

    days_elapsed = (now - baseline).total_seconds() / 86400
    missed_cycles = int(days_elapsed / cycle_days)

    if missed_cycles >= 3:
        idx = FREQ_ORDER.index(customer.follow_freq)
        if idx < len(FREQ_ORDER) - 1:
            customer.follow_freq = FREQ_ORDER[idx + 1]
            customer.consecutive_miss_cycles = 0
            customer.follow_freq_updated_at = now.strftime("%Y-%m-%d %H:%M:%S")
            db.commit()


def _can_access(customer: Customer, current_user: User) -> bool:
    role = current_user.role.name
    if role in ("super_admin", "boss"):
        return True
    return customer.owner_id == current_user.id


# ── Global follow-up list（必须在 /{customer_id} 路由之前注册）─────────────────

class FollowUpListItem(BaseModel):
    id: int
    customer_id: int
    customer_name: str
    content: str
    is_effective: bool
    created_at: str
    creator_name: str
    model_config = {"from_attributes": True}


class FollowUpListPage(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[FollowUpListItem]


@router.get("/follow-ups/all", response_model=FollowUpListPage)
def list_all_follow_ups(
    keyword: Optional[str] = None,   # 客户名称 / 跟进内容 / 创建人
    today: bool = False,              # 仅今日
    effective: Optional[bool] = None, # True=有效 False=无效 None=全部
    page: int = 1,
    page_size: int = 10,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    from datetime import date as _date
    role = current.role.name
    Creator = aliased(User)
    q = (
        db.query(FollowUpRecord, Customer.company_name, Creator.full_name)
        .join(Customer, FollowUpRecord.customer_id == Customer.id)
        .join(Creator, FollowUpRecord.created_by == Creator.id)
    )
    if role == "salesperson":
        q = q.filter(Customer.owner_id == current.id)
    if keyword:
        q = q.filter(
            Customer.company_name.ilike(f"%{keyword}%") |
            FollowUpRecord.content.ilike(f"%{keyword}%") |
            Creator.full_name.ilike(f"%{keyword}%")
        )
    if today:
        from datetime import date as _date
        today_str = _date.today().isoformat()
        q = q.filter(FollowUpRecord.created_at.like(f"{today_str}%"))
    if effective is not None:
        q = q.filter(FollowUpRecord.is_effective == effective)
    total = q.count()
    rows = (
        q.order_by(FollowUpRecord.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    items = [
        FollowUpListItem(
            id=r.id,
            customer_id=r.customer_id,
            customer_name=company_name,
            content=r.content,
            is_effective=r.is_effective,
            created_at=r.created_at,
            creator_name=creator_name,
        )
        for r, company_name, creator_name in rows
    ]
    return FollowUpListPage(total=total, page=page, page_size=page_size, items=items)


# ── List ──────────────────────────────────────────────────────────────────────

@router.get("/", response_model=list[CustomerOut])
def list_customers(
    company_name: Optional[str] = None,
    country: Optional[str] = None,
    contact_name: Optional[str] = None,
    contact: Optional[str] = None,
    today_follow: bool = False,   # 仅返回今日有跟进记录的客户
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    role = current.role.name
    q = db.query(Customer)
    if role == "salesperson":
        q = q.filter(Customer.owner_id == current.id)
    if company_name:
        q = q.filter(Customer.company_name.ilike(f"%{company_name}%"))
    if country:
        q = q.filter(Customer.country.ilike(f"%{country}%"))
    if contact_name:
        q = q.filter(Customer.contact_name.ilike(f"%{contact_name}%"))
    if contact:
        q = q.filter(
            (Customer.email.ilike(f"%{contact}%")) |
            (Customer.phone.ilike(f"%{contact}%"))
        )
    if today_follow:
        from datetime import date as _date
        today_str = _date.today().isoformat()
        followed_ids = {
            r.customer_id for r in
            db.query(FollowUpRecord.customer_id)
            .filter(FollowUpRecord.created_at.like(f"{today_str}%"))
            .all()
        }
        q = q.filter(Customer.id.in_(followed_ids))
    customers = q.order_by(Customer.id.desc()).all()
    for c in customers:
        _check_downgrade(c, db)
    return customers


# ── Create ────────────────────────────────────────────────────────────────────

@router.post("/", response_model=CustomerOut, status_code=status.HTTP_201_CREATED)
def create_customer(
    body: CustomerCreate,
    db: Session = Depends(get_db),
    current: User = Depends(require_roles("salesperson", "super_admin")),
):
    if body.grade not in ("key", "normal", "potential"):
        raise HTTPException(status_code=400, detail="客户分级无效")

    now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    customer = Customer(
        company_name=body.company_name,
        country=body.country,
        contact_name=body.contact_name,
        email=body.email,
        phone=body.phone,
        trade_terms=body.trade_terms,
        payment_terms=body.payment_terms,
        grade=body.grade,
        owner_id=current.id,
        follow_freq="daily",
        follow_freq_updated_at=now_str,
        consecutive_miss_cycles=0,
        is_active=True,
        created_at=now_str,
        updated_at=now_str,
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


# ── Detail ────────────────────────────────────────────────────────────────────

@router.get("/{customer_id}", response_model=CustomerOut)
def get_customer(
    customer_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    customer = db.get(Customer, customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="客户不存在")
    if not _can_access(customer, current):
        raise HTTPException(status_code=403, detail="无权限访问该客户")
    _check_downgrade(customer, db)
    return customer


# ── Update ────────────────────────────────────────────────────────────────────

@router.put("/{customer_id}", response_model=CustomerOut)
def update_customer(
    customer_id: int,
    body: CustomerUpdate,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    customer = db.get(Customer, customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="客户不存在")
    if not _can_access(customer, current):
        raise HTTPException(status_code=403, detail="无权限修改该客户")

    for field, val in body.model_dump(exclude_none=True).items():
        if field == "grade" and val not in ("key", "normal", "potential"):
            raise HTTPException(status_code=400, detail="客户分级无效")
        setattr(customer, field, val)

    customer.updated_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    db.commit()
    db.refresh(customer)
    return customer


# ── Manual frequency upgrade ──────────────────────────────────────────────────

@router.put("/{customer_id}/upgrade-freq", response_model=CustomerOut)
def upgrade_freq(
    customer_id: int,
    body: FreqUpgradeBody,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    customer = db.get(Customer, customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="客户不存在")
    if not _can_access(customer, current):
        raise HTTPException(status_code=403, detail="无权限修改该客户")

    if body.freq not in FREQ_ORDER:
        raise HTTPException(status_code=400, detail="频次无效")

    current_idx = FREQ_ORDER.index(customer.follow_freq)
    new_idx = FREQ_ORDER.index(body.freq)
    if new_idx >= current_idx:
        raise HTTPException(status_code=400, detail="只能手动升级跟进频次")

    now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    customer.follow_freq = body.freq
    customer.follow_freq_updated_at = now_str
    customer.consecutive_miss_cycles = 0
    db.commit()
    db.refresh(customer)
    return customer


# ── Follow-up records ─────────────────────────────────────────────────────────

class FollowUpPage(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[FollowUpOut]


@router.get("/{customer_id}/follow-ups", response_model=FollowUpPage)
def list_follow_ups(
    customer_id: int,
    page: int = 1,
    page_size: int = 10,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    customer = db.get(Customer, customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="客户不存在")
    if not _can_access(customer, current):
        raise HTTPException(status_code=403, detail="无权限访问该客户")

    base_q = db.query(FollowUpRecord).filter(FollowUpRecord.customer_id == customer_id)
    total = base_q.count()
    items = (
        base_q
        .order_by(FollowUpRecord.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return FollowUpPage(total=total, page=page, page_size=page_size, items=items)


@router.post(
    "/{customer_id}/follow-ups",
    response_model=FollowUpOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_follow_up(
    customer_id: int,
    content: str = Form(...),
    is_effective: bool = Form(...),
    images: list[UploadFile] = File(default=[]),
    db: Session = Depends(get_db),
    current: User = Depends(require_roles("salesperson", "super_admin")),
):
    customer = db.get(Customer, customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="客户不存在")
    if not _can_access(customer, current):
        raise HTTPException(status_code=403, detail="无权限访问该客户")

    now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    record = FollowUpRecord(
        customer_id=customer_id,
        content=content,
        is_effective=is_effective,
        created_by=current.id,
        created_at=now_str,
    )
    db.add(record)
    db.flush()  # get record.id before saving images

    # Save uploaded images
    upload_dir = os.path.join(settings.UPLOAD_DIR, "follow_ups", str(customer_id))
    os.makedirs(upload_dir, exist_ok=True)

    for file in images:
        if not file.filename:
            continue
        ext = os.path.splitext(file.filename)[1].lower()
        saved_name = f"{uuid.uuid4().hex}{ext}"
        saved_path = os.path.join(upload_dir, saved_name)
        data = await file.read()
        with open(saved_path, "wb") as f:
            f.write(data)

        rel_path = f"/uploads/follow_ups/{customer_id}/{saved_name}"
        img = FollowUpImage(
            follow_up_id=record.id,
            file_path=rel_path,
            file_name=file.filename,
        )
        db.add(img)

    # If effective, reset consecutive miss cycles
    if is_effective:
        customer.consecutive_miss_cycles = 0

    db.commit()
    db.refresh(record)
    return record
