from datetime import date, datetime
from decimal import Decimal
from typing import Optional

import os
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.core.deps import get_current_user, require_roles
from app.database import get_db
from app.models.customer import Customer
from app.models.pricing_sheet import PricingSheet, PricingSheetImage, PricingSheetItem
from app.models.user import User
from app.schemas.pricing_sheet import (
    PricingSheetCreate,
    PricingSheetListItem,
    PricingSheetOut,
    PricingSheetUpdate,
)

router = APIRouter(prefix="/pricing-sheets", tags=["核价单"])


def _calc_price(item_data, exchange_rate: float, sea_freight: float | None, tons_per_container: float | None, trade_terms: str | None) -> Decimal:
    """按公式计算报价"""
    cost = Decimal(str(item_data.cost))
    inland = Decimal(str(item_data.inland_freight))
    packing = Decimal(str(item_data.packing_cost))
    port = Decimal(str(item_data.port_charges))
    profit = Decimal(str(item_data.profit))
    rate = Decimal(str(exchange_rate))

    fob_price = (cost + inland + packing + port + profit) / rate

    is_cif = trade_terms and trade_terms.upper() == "CIF"
    if is_cif and sea_freight and tons_per_container and tons_per_container > 0:
        fob_price += Decimal(str(sea_freight)) / Decimal(str(tons_per_container))

    return fob_price.quantize(Decimal("0.0001"))


def _generate_ps_number(db: Session, salesperson_code: str) -> str:
    today = date.today().strftime("%Y%m%d")
    prefix = f"QT-XIMO{salesperson_code}{today}-"
    used = {
        int(r[0].split("-")[-1])
        for r in db.query(PricingSheet.ps_number).filter(PricingSheet.ps_number.like(f"{prefix}%")).all()
    }
    seq = 1
    while seq in used:
        seq += 1
    return f"{prefix}{seq:02d}"


def _can_access(user: User, ps: PricingSheet) -> bool:
    role = user.role.name
    if role in ("super_admin", "boss"):
        return True
    return role == "salesperson" and ps.salesperson_id == user.id


def _can_edit(user: User, ps: PricingSheet) -> bool:
    role = user.role.name
    if role == "super_admin":
        return True
    # draft 或 confirmed（所有PI已作废后恢复的状态）均可编辑
    return role == "salesperson" and ps.salesperson_id == user.id and ps.status in ("draft", "confirmed")


@router.get("/", response_model=list[PricingSheetListItem])
def list_pricing_sheets(
    status: Optional[str] = Query(None),
    ps_number: Optional[str] = Query(None),
    customer_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(PricingSheet)
    if current_user.role.name == "salesperson":
        q = q.filter(PricingSheet.salesperson_id == current_user.id)
    if status:
        q = q.filter(PricingSheet.status == status)
    if ps_number:
        q = q.filter(PricingSheet.ps_number.ilike(f"%{ps_number}%"))
    if customer_id:
        q = q.filter(PricingSheet.customer_id == customer_id)
    return (
        q.order_by(PricingSheet.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )


@router.post("/", response_model=PricingSheetOut)
def create_pricing_sheet(
    body: PricingSheetCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("salesperson", "super_admin")),
):
    code = current_user.salesperson_code
    if not code:
        raise HTTPException(status_code=400, detail="当前用户未分配业务员编码")

    if body.customer_id:
        customer = db.get(Customer, body.customer_id)
        if not customer:
            raise HTTPException(status_code=404, detail="客户不存在")
        if current_user.role.name == "salesperson" and customer.owner_id != current_user.id:
            raise HTTPException(status_code=403, detail="只能关联自己名下的客户")

    now = datetime.utcnow().isoformat()

    for _attempt in range(5):
        ps = PricingSheet(
            ps_number=_generate_ps_number(db, code),
            customer_id=body.customer_id,
            salesperson_id=current_user.id,
            trade_terms=body.trade_terms,
            currency=body.currency,
            exchange_rate=body.exchange_rate,
            sea_freight=body.sea_freight,
            tons_per_container=body.tons_per_container,
            remarks=body.remarks,
            status="draft",
            created_by=current_user.id,
            created_at=now,
            updated_at=now,
        )
        db.add(ps)
        try:
            db.flush()
            break
        except IntegrityError:
            db.rollback()
    else:
        raise HTTPException(status_code=500, detail="QT 编号生成冲突，请重试")

    for idx, item_data in enumerate(body.items):
        calc = _calc_price(item_data, body.exchange_rate, body.sea_freight, body.tons_per_container, body.trade_terms)
        db.add(PricingSheetItem(
            ps_id=ps.id,
            product_id=item_data.product_id,
            grade_label=item_data.grade_label,
            hscode=item_data.hscode,
            description=item_data.description,
            quantity=item_data.quantity,
            unit=item_data.unit,
            cost=item_data.cost,
            inland_freight=item_data.inland_freight,
            packing_cost=item_data.packing_cost,
            port_charges=item_data.port_charges,
            profit=item_data.profit,
            calculated_price=calc,
            sort_order=item_data.sort_order or idx,
        ))

    db.commit()
    db.refresh(ps)
    return ps


@router.get("/{ps_id}", response_model=PricingSheetOut)
def get_pricing_sheet(
    ps_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ps = db.get(PricingSheet, ps_id)
    if not ps:
        raise HTTPException(status_code=404, detail="核价单不存在")
    if not _can_access(current_user, ps):
        raise HTTPException(status_code=403, detail="权限不足")
    return ps


@router.put("/{ps_id}", response_model=PricingSheetOut)
def update_pricing_sheet(
    ps_id: int,
    body: PricingSheetUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ps = db.get(PricingSheet, ps_id)
    if not ps:
        raise HTTPException(status_code=404, detail="核价单不存在")
    if not _can_edit(current_user, ps):
        raise HTTPException(status_code=403, detail="无法编辑：权限不足或状态不是草稿")

    if body.customer_id is not None:
        if body.customer_id > 0:
            customer = db.get(Customer, body.customer_id)
            if not customer:
                raise HTTPException(status_code=404, detail="客户不存在")
        ps.customer_id = body.customer_id or None

    for field in ("trade_terms", "currency", "exchange_rate", "sea_freight", "tons_per_container", "remarks"):
        val = getattr(body, field)
        if val is not None:
            setattr(ps, field, val)

    # 取最新有效值用于重新计算
    rate = float(body.exchange_rate or ps.exchange_rate)
    sea = float(body.sea_freight or ps.sea_freight or 0) or None
    tons = float(body.tons_per_container or ps.tons_per_container or 0) or None
    terms = body.trade_terms or ps.trade_terms

    if body.items is not None:
        db.query(PricingSheetItem).filter(PricingSheetItem.ps_id == ps_id).delete()
        for idx, item_data in enumerate(body.items):
            calc = _calc_price(item_data, rate, sea, tons, terms)
            db.add(PricingSheetItem(
                ps_id=ps.id,
                product_id=item_data.product_id,
                grade_label=item_data.grade_label,
                hscode=item_data.hscode,
                description=item_data.description,
                quantity=item_data.quantity,
                unit=item_data.unit,
                cost=item_data.cost,
                inland_freight=item_data.inland_freight,
                packing_cost=item_data.packing_cost,
                port_charges=item_data.port_charges,
                profit=item_data.profit,
                calculated_price=calc,
                sort_order=item_data.sort_order or idx,
            ))

    ps.updated_at = datetime.utcnow().isoformat()
    db.commit()
    db.refresh(ps)
    return ps


@router.patch("/{ps_id}/confirm", response_model=PricingSheetOut)
def confirm_pricing_sheet(
    ps_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ps = db.get(PricingSheet, ps_id)
    if not ps:
        raise HTTPException(status_code=404, detail="核价单不存在")
    if not _can_edit(current_user, ps):
        raise HTTPException(status_code=403, detail="权限不足")
    if ps.status != "draft":
        raise HTTPException(status_code=400, detail="只有草稿状态可以确认")
    if not ps.items:
        raise HTTPException(status_code=400, detail="核价单没有产品明细，无法确认")
    ps.status = "confirmed"
    ps.updated_at = datetime.utcnow().isoformat()
    db.commit()
    db.refresh(ps)
    return ps


@router.post("/{ps_id}/convert-to-pi", summary="核价单转PI（报价单）")
def convert_to_pi(
    ps_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("salesperson", "super_admin")),
):
    from app.models.quotation import Quotation, QuotationItem

    ps = db.get(PricingSheet, ps_id)
    if not ps:
        raise HTTPException(status_code=404, detail="核价单不存在")
    if not _can_access(current_user, ps):
        raise HTTPException(status_code=403, detail="权限不足")
    if ps.status != "confirmed":
        raise HTTPException(status_code=400, detail="只有已确认的核价单才能转PI，请先确认核价")

    # 生成 PI 编号
    code = current_user.salesperson_code
    if not code:
        raise HTTPException(status_code=400, detail="当前用户未分配业务员编码")

    today = date.today().strftime("%Y%m%d")
    pi_prefix = f"PI-XIMO{code}{today}-"
    pi_count = db.query(func.count(Quotation.id)).filter(Quotation.pi_number.like(f"{pi_prefix}%")).scalar()
    pi_number = f"{pi_prefix}{pi_count + 1:02d}"

    now = datetime.utcnow().isoformat()
    quotation = Quotation(
        pi_number=pi_number,
        pricing_sheet_id=ps.id,
        customer_id=ps.customer_id,
        salesperson_id=ps.salesperson_id,
        currency=ps.currency,
        exchange_rate=ps.exchange_rate,
        trade_terms=ps.trade_terms,
        status="draft",
        created_by=current_user.id,
        created_at=now,
        updated_at=now,
    )
    db.add(quotation)
    db.flush()

    for item in sorted(ps.items, key=lambda x: x.sort_order):
        price = item.calculated_price or 0
        db.add(QuotationItem(
            quotation_id=quotation.id,
            product_id=item.product_id,
            grade_label=item.grade_label,
            hscode=item.hscode,
            description=item.description,
            quantity=item.quantity,
            unit=item.unit,
            unit_price=price,
            unit_price_internal=float(item.cost) / float(ps.exchange_rate) if ps.exchange_rate else None,
            sort_order=item.sort_order,
        ))

    ps.status = "converted"
    ps.updated_at = now
    db.commit()
    db.refresh(quotation)
    return {"pi_number": quotation.pi_number, "quotation_id": quotation.id}


VALID_CATEGORIES = {"cost_notes", "freight_notes"}


@router.post("/{ps_id}/images/{category}", summary="上传说明图片")
async def upload_image(
    ps_id: int,
    category: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if category not in VALID_CATEGORIES:
        raise HTTPException(status_code=400, detail="category 必须是 cost_notes 或 freight_notes")

    ps = db.get(PricingSheet, ps_id)
    if not ps:
        raise HTTPException(status_code=404, detail="核价单不存在")
    if not _can_access(current_user, ps):
        raise HTTPException(status_code=403, detail="权限不足")

    upload_dir = os.path.join(settings.UPLOAD_DIR, "pricing_sheets", str(ps_id), category)
    os.makedirs(upload_dir, exist_ok=True)

    ext = os.path.splitext(file.filename or "img.jpg")[1].lower() or ".jpg"
    saved_name = f"{uuid.uuid4().hex}{ext}"
    saved_path = os.path.join(upload_dir, saved_name)
    data = await file.read()
    with open(saved_path, "wb") as f:
        f.write(data)

    rel_path = f"/uploads/pricing_sheets/{ps_id}/{category}/{saved_name}"
    img = PricingSheetImage(
        ps_id=ps_id,
        category=category,
        file_path=rel_path,
        file_name=file.filename or saved_name,
        uploaded_by=current_user.id,
        uploaded_at=datetime.utcnow().isoformat(),
    )
    db.add(img)
    db.commit()
    db.refresh(img)
    return {"id": img.id, "file_path": img.file_path, "file_name": img.file_name}


@router.delete("/{ps_id}/images/{image_id}", summary="删除说明图片")
def delete_image(
    ps_id: int,
    image_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ps = db.get(PricingSheet, ps_id)
    if not ps:
        raise HTTPException(status_code=404, detail="核价单不存在")
    if not _can_access(current_user, ps):
        raise HTTPException(status_code=403, detail="权限不足")

    img = db.get(PricingSheetImage, image_id)
    if not img or img.ps_id != ps_id:
        raise HTTPException(status_code=404, detail="图片不存在")

    # 删除物理文件
    full_path = os.path.join(settings.UPLOAD_DIR, img.file_path.removeprefix("/uploads/"))
    if os.path.exists(full_path):
        os.remove(full_path)

    db.delete(img)
    db.commit()
    return {"ok": True}
