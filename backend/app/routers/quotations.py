from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_roles
from app.database import get_db
from app.models.customer import Customer
from app.models.quotation import Quotation, QuotationItem
from app.models.user import User
from app.schemas.quotation import (
    QuotationCreate,
    QuotationListItem,
    QuotationOut,
    QuotationUpdate,
)

router = APIRouter(prefix="/quotations", tags=["询报价"])

ALLOWED_STATUS_TRANSITIONS = {
    "draft": {"sent", "expired"},
    "sent": {"won", "expired"},
    "won": set(),
    "expired": set(),
}


def _generate_pi_number(db: Session, salesperson_code: str) -> str:
    today = date.today().strftime("%Y%m%d")
    prefix = f"PI-XIMO{salesperson_code}{today}-"
    used = {
        int(r[0].split("-")[-1])
        for r in db.query(Quotation.pi_number).filter(Quotation.pi_number.like(f"{prefix}%")).all()
    }
    seq = 1
    while seq in used:
        seq += 1
    return f"{prefix}{seq:02d}"


def _can_access(user: User, quotation: Quotation) -> bool:
    role = user.role.name
    if role in ("super_admin", "boss"):
        return True
    if role == "salesperson":
        return quotation.salesperson_id == user.id
    return False


def _can_edit(user: User, quotation: Quotation) -> bool:
    role = user.role.name
    if role == "super_admin":
        return True
    if role == "salesperson" and quotation.salesperson_id == user.id:
        return quotation.status == "draft"
    return False


@router.get("/", response_model=list[QuotationListItem])
def list_quotations(
    customer_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    pi_number: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(Quotation)
    role = current_user.role.name
    if role == "salesperson":
        q = q.filter(Quotation.salesperson_id == current_user.id)
    if customer_id:
        q = q.filter(Quotation.customer_id == customer_id)
    if status:
        q = q.filter(Quotation.status == status)
    if pi_number:
        q = q.filter(Quotation.pi_number.ilike(f"%{pi_number}%"))

    return (
        q.order_by(Quotation.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )


@router.post("/", response_model=QuotationOut)
def create_quotation(
    body: QuotationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("salesperson", "super_admin")),
):
    code = current_user.salesperson_code
    if not code:
        raise HTTPException(status_code=400, detail="当前用户未分配业务员编码，无法创建报价单")

    customer = db.get(Customer, body.customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="客户不存在")

    if current_user.role.name == "salesperson" and customer.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="只能为自己名下的客户创建报价单")

    now = datetime.utcnow().isoformat()

    for _attempt in range(5):
        pi_number = _generate_pi_number(db, code)
        quotation = Quotation(
            pi_number=pi_number,
            customer_id=body.customer_id,
            salesperson_id=current_user.id,
            currency=body.currency,
            exchange_rate=body.exchange_rate,
            trade_terms=body.trade_terms,
            delivery_date=body.delivery_date,
            valid_until=body.valid_until,
            remarks=body.remarks,
            contact_person=body.contact_person,
            payment_terms=body.payment_terms,
            commodity=body.commodity,
            packing=body.packing or "EXPORT STANDARD",
            port_of_loading=body.port_of_loading,
            destination_port=body.destination_port,
            note_pi=body.note_pi,
            status="draft",
            created_by=current_user.id,
            created_at=now,
            updated_at=now,
        )
        db.add(quotation)
        try:
            db.flush()
            break
        except IntegrityError:
            db.rollback()
    else:
        raise HTTPException(status_code=500, detail="PI 编号生成冲突，请重试")

    for idx, item_data in enumerate(body.items):
        item = QuotationItem(
            quotation_id=quotation.id,
            product_id=item_data.product_id,
            grade_label=item_data.grade_label,
            hscode=item_data.hscode,
            description=item_data.description,
            quantity=item_data.quantity,
            unit=item_data.unit,
            unit_price=item_data.unit_price,
            unit_price_internal=item_data.unit_price_internal,
            sort_order=item_data.sort_order if item_data.sort_order else idx,
        )
        db.add(item)

    db.commit()
    db.refresh(quotation)
    return quotation


@router.get("/{quotation_id}", response_model=QuotationOut)
def get_quotation(
    quotation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    quotation = db.get(Quotation, quotation_id)
    if not quotation:
        raise HTTPException(status_code=404, detail="报价单不存在")
    if not _can_access(current_user, quotation):
        raise HTTPException(status_code=403, detail="权限不足")
    return quotation


@router.put("/{quotation_id}", response_model=QuotationOut)
def update_quotation(
    quotation_id: int,
    body: QuotationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    quotation = db.get(Quotation, quotation_id)
    if not quotation:
        raise HTTPException(status_code=404, detail="报价单不存在")
    if not _can_edit(current_user, quotation):
        raise HTTPException(status_code=403, detail="无法编辑：权限不足或报价单状态不是草稿")

    if body.customer_id is not None:
        customer = db.get(Customer, body.customer_id)
        if not customer:
            raise HTTPException(status_code=404, detail="客户不存在")
        if current_user.role.name == "salesperson" and customer.owner_id != current_user.id:
            raise HTTPException(status_code=403, detail="只能关联自己名下的客户")
        quotation.customer_id = body.customer_id

    for field in (
        "currency", "exchange_rate", "trade_terms", "delivery_date", "valid_until",
        "remarks", "contact_person", "payment_terms", "commodity", "packing",
        "port_of_loading", "destination_port", "note_pi",
    ):
        val = getattr(body, field)
        if val is not None:
            setattr(quotation, field, val)

    if body.items is not None:
        db.query(QuotationItem).filter(QuotationItem.quotation_id == quotation_id).delete()
        for idx, item_data in enumerate(body.items):
            item = QuotationItem(
                quotation_id=quotation.id,
                product_id=item_data.product_id,
                grade_label=item_data.grade_label,
                hscode=item_data.hscode,
                description=item_data.description,
                quantity=item_data.quantity,
                unit=item_data.unit,
                unit_price=item_data.unit_price,
                unit_price_internal=item_data.unit_price_internal,
                sort_order=item_data.sort_order if item_data.sort_order else idx,
            )
            db.add(item)

    quotation.updated_at = datetime.utcnow().isoformat()
    db.commit()
    db.refresh(quotation)
    return quotation


@router.patch("/{quotation_id}/status", response_model=QuotationOut)
def update_status(
    quotation_id: int,
    status: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    quotation = db.get(Quotation, quotation_id)
    if not quotation:
        raise HTTPException(status_code=404, detail="报价单不存在")
    if not _can_access(current_user, quotation):
        raise HTTPException(status_code=403, detail="权限不足")
    if current_user.role.name == "boss":
        raise HTTPException(status_code=403, detail="老板角色无法修改状态")

    allowed = ALLOWED_STATUS_TRANSITIONS.get(quotation.status, set())
    if status not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"状态流转不合法：{quotation.status} → {status}",
        )

    quotation.status = status
    quotation.updated_at = datetime.utcnow().isoformat()

    # PI 作废时：若来自核价单，检查该核价单所有 PI 是否全部作废
    # 全部作废则恢复核价单为 confirmed 状态，允许重新编辑/转PI
    if status == "expired" and quotation.pricing_sheet_id:
        from app.models.pricing_sheet import PricingSheet
        ps = db.get(PricingSheet, quotation.pricing_sheet_id)
        if ps and ps.status == "converted":
            sibling_statuses = (
                db.query(Quotation.status)
                .filter(
                    Quotation.pricing_sheet_id == ps.id,
                    Quotation.id != quotation.id,
                )
                .all()
            )
            # 当前这条已设为 expired，其余兄弟也全是 expired 则解锁
            all_expired = all(s[0] == "expired" for s in sibling_statuses)
            if all_expired:
                ps.status = "confirmed"
                ps.updated_at = datetime.utcnow().isoformat()

    db.commit()
    db.refresh(quotation)
    return quotation


@router.get("/{quotation_id}/generate-pi", summary="生成 PI PDF")
def generate_pi(
    quotation_id: int,
    internal: bool = Query(False, description="True=内部版（含内部单价），False=客户版"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.models.company import CompanyInfo
    from app.services.pi_pdf import generate_pi_pdf

    quotation = db.get(Quotation, quotation_id)
    if not quotation:
        raise HTTPException(status_code=404, detail="报价单不存在")
    if not _can_access(current_user, quotation):
        raise HTTPException(status_code=403, detail="权限不足")

    company = db.query(CompanyInfo).first()

    pdf_bytes = generate_pi_pdf(quotation, company, is_internal=internal)

    suffix = "internal" if internal else "client"
    filename = f"{quotation.pi_number}-{suffix}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/{quotation_id}/convert-to-order", summary="PI 一键转单")
def convert_to_order(
    quotation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("salesperson", "super_admin")),
):
    from app.models.order import Order, OrderItem

    quotation = db.get(Quotation, quotation_id)
    if not quotation:
        raise HTTPException(status_code=404, detail="报价单不存在")
    if not _can_access(current_user, quotation):
        raise HTTPException(status_code=403, detail="权限不足")
    if quotation.status != "won":
        raise HTTPException(status_code=400, detail="只有已成交的报价单才能转单")

    existing = db.query(Order).filter(Order.quotation_id == quotation_id).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"该报价单已转单，订单号：{existing.so_number}")

    code = current_user.salesperson_code
    today = date.today().strftime("%Y%m%d")
    so_prefix = f"SO-XIMO{code}{today}-"
    so_count = db.query(func.count(Order.id)).filter(Order.so_number.like(f"{so_prefix}%")).scalar()
    so_number = f"{so_prefix}{so_count + 1:02d}"

    now = datetime.utcnow().isoformat()
    order = Order(
        so_number=so_number,
        quotation_id=quotation.id,
        customer_id=quotation.customer_id,
        salesperson_id=quotation.salesperson_id,
        currency=quotation.currency,
        exchange_rate=quotation.exchange_rate,
        trade_terms=quotation.trade_terms,
        remarks=quotation.remarks,
        status="confirmed",
        created_by=current_user.id,
        created_at=now,
        updated_at=now,
    )
    db.add(order)
    db.flush()

    for item in quotation.items:
        db.add(OrderItem(
            order_id=order.id,
            product_id=item.product_id,
            description=item.description,
            quantity=item.quantity,
            unit=item.unit,
            unit_price=item.unit_price,
            unit_price_internal=item.unit_price_internal,
            sort_order=item.sort_order,
        ))

    db.commit()
    db.refresh(order)
    return {"so_number": order.so_number, "order_id": order.id}
