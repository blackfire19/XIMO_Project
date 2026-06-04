import os
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.order import Order
from app.models.shipment import Shipment
from app.models.document import OrderAttachment
from app.models.user import User
from app.schemas.order import (
    OrderListItem,
    OrderOut,
    OrderStatusUpdate,
    ShipmentCreate,
    ShipmentOut,
    ShipmentUpdate,
    OrderAttachmentOut,
)
from app.config import settings

router = APIRouter(prefix="/orders", tags=["订单管理"])

ALLOWED_STATUS_TRANSITIONS = {
    "confirmed": {"production"},
    "production": {"ready"},
    "ready": {"shipped"},
    "shipped": {"completed"},
    "completed": set(),
}

SHIPMENT_STATUS_TRANSITIONS = {
    "planned": {"loaded"},
    "loaded": {"transit"},
    "transit": {"arrived"},
    "arrived": set(),
}

STATUS_LABELS = {
    "confirmed": "已确认",
    "production": "生产备货中",
    "ready": "待出运",
    "shipped": "已出运",
    "completed": "已完结",
}

DOC_TYPES = {"MTC", "CO", "export_permit", "customs", "other"}


def _can_access(user: User, order: Order) -> bool:
    role = user.role.name
    if role in ("super_admin", "boss"):
        return True
    if role == "salesperson":
        return order.salesperson_id == user.id
    return False


def _can_edit(user: User, order: Order) -> bool:
    role = user.role.name
    if role == "super_admin":
        return True
    if role == "salesperson":
        return order.salesperson_id == user.id
    return False


@router.get("/", response_model=list[OrderListItem])
def list_orders(
    customer_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    so_number: Optional[str] = Query(None),
    active: bool = Query(False),   # True = 筛选进行中（非已完结）
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(Order)
    role = current_user.role.name
    if role == "salesperson":
        q = q.filter(Order.salesperson_id == current_user.id)
    if customer_id:
        q = q.filter(Order.customer_id == customer_id)
    if status:
        q = q.filter(Order.status == status)
    if active:
        q = q.filter(Order.status != "completed")
    if so_number:
        q = q.filter(Order.so_number.ilike(f"%{so_number}%"))

    return (
        q.order_by(Order.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )


@router.get("/{order_id}", response_model=OrderOut)
def get_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    if not _can_access(current_user, order):
        raise HTTPException(status_code=403, detail="权限不足")
    return order


@router.patch("/{order_id}/status", response_model=OrderOut)
def update_order_status(
    order_id: int,
    body: OrderStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    if not _can_edit(current_user, order):
        raise HTTPException(status_code=403, detail="权限不足")
    if current_user.role.name == "boss":
        raise HTTPException(status_code=403, detail="老板角色无法修改状态")

    allowed = ALLOWED_STATUS_TRANSITIONS.get(order.status, set())
    if body.status not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"状态流转不合法：{STATUS_LABELS.get(order.status, order.status)} → {STATUS_LABELS.get(body.status, body.status)}",
        )

    order.status = body.status
    if body.est_ready_date is not None:
        order.est_ready_date = body.est_ready_date
    order.updated_at = datetime.utcnow().isoformat()
    db.commit()
    db.refresh(order)
    return order


# ── 出运管理 ──────────────────────────────────────────────

@router.get("/{order_id}/shipments", response_model=list[ShipmentOut])
def list_shipments(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    if not _can_access(current_user, order):
        raise HTTPException(status_code=403, detail="权限不足")
    return order.shipments


@router.post("/{order_id}/shipments", response_model=ShipmentOut)
def add_shipment(
    order_id: int,
    body: ShipmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    if not _can_edit(current_user, order):
        raise HTTPException(status_code=403, detail="权限不足")

    now = datetime.utcnow().isoformat()
    shipment = Shipment(
        order_id=order_id,
        ship_type=body.ship_type,
        status="planned",
        container_type=body.container_type,
        container_number=body.container_number,
        seal_number=body.seal_number,
        vessel_voyage=body.vessel_voyage,
        etd=body.etd,
        eta=body.eta,
        bl_number=body.bl_number,
        weight_mt=body.weight_mt,
        remarks=body.remarks,
        created_by=current_user.id,
        created_at=now,
        updated_at=now,
    )
    db.add(shipment)
    db.commit()
    db.refresh(shipment)
    return shipment


@router.put("/{order_id}/shipments/{shipment_id}", response_model=ShipmentOut)
def update_shipment(
    order_id: int,
    shipment_id: int,
    body: ShipmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    if not _can_edit(current_user, order):
        raise HTTPException(status_code=403, detail="权限不足")

    shipment = db.get(Shipment, shipment_id)
    if not shipment or shipment.order_id != order_id:
        raise HTTPException(status_code=404, detail="出运记录不存在")

    if body.status and body.status != shipment.status:
        allowed = SHIPMENT_STATUS_TRANSITIONS.get(shipment.status, set())
        if body.status not in allowed:
            raise HTTPException(status_code=400, detail=f"出运状态流转不合法：{shipment.status} → {body.status}")
        shipment.status = body.status

    for field in ("ship_type", "container_type", "container_number", "seal_number",
                  "vessel_voyage", "etd", "eta", "bl_number", "weight_mt", "remarks"):
        val = getattr(body, field)
        if val is not None:
            setattr(shipment, field, val)

    shipment.updated_at = datetime.utcnow().isoformat()
    db.commit()
    db.refresh(shipment)
    return shipment


@router.delete("/{order_id}/shipments/{shipment_id}", status_code=204)
def delete_shipment(
    order_id: int,
    shipment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    if not _can_edit(current_user, order):
        raise HTTPException(status_code=403, detail="权限不足")
    shipment = db.get(Shipment, shipment_id)
    if not shipment or shipment.order_id != order_id:
        raise HTTPException(status_code=404, detail="出运记录不存在")
    db.delete(shipment)
    db.commit()


# ── 附件管理 ──────────────────────────────────────────────

@router.get("/{order_id}/attachments", response_model=list[OrderAttachmentOut])
def list_attachments(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    if not _can_access(current_user, order):
        raise HTTPException(status_code=403, detail="权限不足")
    return order.attachments


@router.post("/{order_id}/attachments", response_model=OrderAttachmentOut)
async def upload_attachment(
    order_id: int,
    doc_type: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if doc_type not in DOC_TYPES:
        raise HTTPException(status_code=400, detail=f"doc_type 必须是 {', '.join(DOC_TYPES)} 之一")

    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    if not _can_edit(current_user, order):
        raise HTTPException(status_code=403, detail="权限不足")

    upload_dir = os.path.join(settings.UPLOAD_DIR, "order_attachments", str(order_id))
    os.makedirs(upload_dir, exist_ok=True)

    original_name = file.filename or "file"
    ext = os.path.splitext(original_name)[1]
    saved_name = f"{uuid.uuid4().hex}{ext}"
    saved_path = os.path.join(upload_dir, saved_name)

    content = await file.read()
    with open(saved_path, "wb") as f:
        f.write(content)

    rel_path = f"order_attachments/{order_id}/{saved_name}"
    now = datetime.utcnow().isoformat()
    att = OrderAttachment(
        order_id=order_id,
        doc_type=doc_type,
        file_name=original_name,
        file_path=rel_path,
        uploaded_by=current_user.id,
        uploaded_at=now,
    )
    db.add(att)
    db.commit()
    db.refresh(att)
    return att


@router.delete("/{order_id}/attachments/{attachment_id}", status_code=204)
def delete_attachment(
    order_id: int,
    attachment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    if not _can_edit(current_user, order):
        raise HTTPException(status_code=403, detail="权限不足")
    att = db.get(OrderAttachment, attachment_id)
    if not att or att.order_id != order_id:
        raise HTTPException(status_code=404, detail="附件不存在")

    full_path = os.path.join(settings.UPLOAD_DIR, att.file_path)
    if os.path.exists(full_path):
        os.remove(full_path)

    db.delete(att)
    db.commit()
