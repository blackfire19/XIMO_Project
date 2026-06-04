import os
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.inquiry import (
    Inquiry, FormalOrder, OrderFile, ShipmentBL,
)
from app.models.user import User
from app.schemas.inquiry import (
    FormalOrderCreate,
    FormalOrderUpdate,
    FormalOrderStatusUpdate,
    FormalOrderListItem,
    FormalOrderOut,
    OrderFileOut,
    BLCreate,
    BLUpdate,
    BLOut,
)
from app.config import settings

router = APIRouter(prefix="/formal-orders", tags=["正式订单"])

ORDER_DOC_TYPES = {"mtc", "pl", "ci", "co", "export_permit", "inspection", "packing", "supplement"}

# 补充附件：不受出运锁定限制，任何状态均可上传/删除
SUPPLEMENT_DOC_TYPE = "supplement"
# 进入这些状态后，正式归档文件只读（仅可查看），不能再上传/删除
FILE_LOCK_STATUSES = {"shipping", "completed"}


def _next_status(order: FormalOrder) -> str | None:
    """线性流转；现货订单跳过「生产中」"""
    s = order.status
    if s == "confirmed":
        return "ready" if order.is_stock else "production"
    if s == "production":
        return "ready"
    if s == "ready":
        return "shipping"
    if s == "shipping":
        return "completed"
    return None
STATUS_LABELS = {
    "confirmed": "已确认",
    "production": "生产中",
    "ready": "待出运",
    "shipping": "出运中",
    "completed": "已完结",
}


def _can_access(user: User, order: FormalOrder) -> bool:
    role = user.role.name
    if role in ("super_admin", "boss"):
        return True
    if role == "salesperson":
        return order.salesperson_id == user.id
    return False


def _can_edit(user: User, order: FormalOrder) -> bool:
    role = user.role.name
    if role == "super_admin":
        return order.status != "completed"
    if role == "salesperson":
        return order.salesperson_id == user.id and order.status != "completed"
    return False


def _gen_so_number(db: Session, salesperson: User) -> str:
    code = salesperson.salesperson_code or "XX"
    today = datetime.now().strftime("%Y%m%d")
    prefix = f"SO-XIMO{code}{today}-"
    used = {
        int(r[0].split("-")[-1])
        for r in db.query(FormalOrder.so_number).filter(FormalOrder.so_number.like(f"{prefix}%")).all()
    }
    seq = 1
    while seq in used:
        seq += 1
    return f"{prefix}{seq:02d}"


# ── 由询价单转正式订单 ─────────────────────────────────────────
@router.post("/", response_model=FormalOrderOut)
def convert_to_order(
    body: FormalOrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    inq = db.get(Inquiry, body.inquiry_id)
    if not inq:
        raise HTTPException(status_code=404, detail="询价单不存在")
    role = current_user.role.name
    if role == "boss":
        raise HTTPException(status_code=403, detail="老板角色无法创建订单")
    if role == "salesperson" and inq.salesperson_id != current_user.id:
        raise HTTPException(status_code=403, detail="权限不足")
    if inq.status != "deposit_received":
        raise HTTPException(status_code=400, detail="仅已收定金的询价单可转为正式订单")
    if inq.formal_order:
        raise HTTPException(status_code=400, detail="该询价单已转为正式订单")

    salesperson = db.get(User, inq.salesperson_id)
    if not salesperson or not salesperson.salesperson_code:
        raise HTTPException(status_code=400, detail="询价单业务员未分配业务员编码，无法生成订单编号")

    now = datetime.utcnow().isoformat()
    for _attempt in range(5):
        order = FormalOrder(
            so_number=_gen_so_number(db, salesperson),
            inquiry_id=inq.id,
            customer_id=inq.customer_id,
            salesperson_id=inq.salesperson_id,
            is_stock=body.is_stock,
            est_production_date=body.est_production_date,
            status="confirmed",
            remarks=body.remarks,
            created_by=current_user.id,
            created_at=now,
            updated_at=now,
        )
        db.add(order)
        inq.status = "converted"
        inq.updated_at = now
        try:
            db.flush()
            break
        except IntegrityError:
            db.rollback()
    else:
        raise HTTPException(status_code=500, detail="SO 编号生成冲突，请重试")

    db.commit()
    db.refresh(order)
    return order


@router.get("/", response_model=list[FormalOrderListItem])
def list_orders(
    customer_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    so_number: Optional[str] = Query(None),
    active: bool = Query(False),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(FormalOrder)
    if current_user.role.name == "salesperson":
        q = q.filter(FormalOrder.salesperson_id == current_user.id)
    if customer_id:
        q = q.filter(FormalOrder.customer_id == customer_id)
    if status:
        q = q.filter(FormalOrder.status == status)
    if active:
        q = q.filter(FormalOrder.status != "completed")
    if so_number:
        q = q.filter(FormalOrder.so_number.ilike(f"%{so_number}%"))
    return (
        q.order_by(FormalOrder.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )


@router.get("/{order_id}", response_model=FormalOrderOut)
def get_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    order = db.get(FormalOrder, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    if not _can_access(current_user, order):
        raise HTTPException(status_code=403, detail="权限不足")
    return order


@router.put("/{order_id}", response_model=FormalOrderOut)
def update_order(
    order_id: int,
    body: FormalOrderUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    order = db.get(FormalOrder, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    if not _can_edit(current_user, order):
        raise HTTPException(status_code=403, detail="权限不足")
    for field in ("is_stock", "est_production_date", "remarks"):
        val = getattr(body, field)
        if val is not None:
            setattr(order, field, val)
    order.updated_at = datetime.utcnow().isoformat()
    db.commit()
    db.refresh(order)
    return order


@router.patch("/{order_id}/status", response_model=FormalOrderOut)
def update_status(
    order_id: int,
    body: FormalOrderStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    order = db.get(FormalOrder, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    if not _can_edit(current_user, order):
        raise HTTPException(status_code=403, detail="权限不足")
    expected = _next_status(order)
    if expected is None or body.status != expected:
        raise HTTPException(
            status_code=400,
            detail=f"状态流转不合法：{STATUS_LABELS.get(order.status, order.status)} → {STATUS_LABELS.get(body.status, body.status)}",
        )
    order.status = body.status
    order.updated_at = datetime.utcnow().isoformat()
    db.commit()
    db.refresh(order)
    return order


# ── 文件归档（MTC/PL/验货/装箱）─────────────────────────────────
@router.post("/{order_id}/files", response_model=OrderFileOut)
async def upload_order_file(
    order_id: int,
    doc_type: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if doc_type not in ORDER_DOC_TYPES:
        raise HTTPException(status_code=400, detail=f"doc_type 必须是 {', '.join(ORDER_DOC_TYPES)} 之一")
    order = db.get(FormalOrder, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    if not _can_edit(current_user, order):
        raise HTTPException(status_code=403, detail="权限不足")
    if doc_type != SUPPLEMENT_DOC_TYPE and order.status in FILE_LOCK_STATUSES:
        raise HTTPException(status_code=400, detail="订单已进入出运阶段，归档文件已锁定，仅可上传补充附件")

    upload_dir = os.path.join(settings.UPLOAD_DIR, "order_files", str(order_id))
    os.makedirs(upload_dir, exist_ok=True)
    original_name = file.filename or "file"
    ext = os.path.splitext(original_name)[1]
    saved_name = f"{uuid.uuid4().hex}{ext}"
    saved_path = os.path.join(upload_dir, saved_name)
    content = await file.read()
    with open(saved_path, "wb") as fp:
        fp.write(content)

    rel_path = f"order_files/{order_id}/{saved_name}"
    rec = OrderFile(
        order_id=order_id,
        doc_type=doc_type,
        file_name=original_name,
        file_path=rel_path,
        uploaded_by=current_user.id,
        uploaded_at=datetime.utcnow().isoformat(),
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return rec


@router.delete("/{order_id}/files/{file_id}", status_code=204)
def delete_order_file(
    order_id: int,
    file_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    order = db.get(FormalOrder, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    if not _can_edit(current_user, order):
        raise HTTPException(status_code=403, detail="权限不足")
    rec = db.get(OrderFile, file_id)
    if not rec or rec.order_id != order_id:
        raise HTTPException(status_code=404, detail="文件不存在")
    if rec.doc_type != SUPPLEMENT_DOC_TYPE and order.status in FILE_LOCK_STATUSES:
        raise HTTPException(status_code=400, detail="订单已进入出运阶段，归档文件已锁定，仅可删除补充附件")
    full_path = os.path.join(settings.UPLOAD_DIR, rec.file_path)
    if os.path.exists(full_path):
        os.remove(full_path)
    db.delete(rec)
    db.commit()


# ── 提单 BL + 集装箱 ──────────────────────────────────────────
@router.post("/{order_id}/bls", response_model=BLOut)
def add_bl(
    order_id: int,
    body: BLCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    order = db.get(FormalOrder, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    if not _can_edit(current_user, order):
        raise HTTPException(status_code=403, detail="权限不足")
    if order.bls:
        raise HTTPException(status_code=400, detail="该订单已有提单，一个订单仅对应一张提单")

    now = datetime.utcnow().isoformat()
    bl = ShipmentBL(
        order_id=order_id,
        ship_type=body.ship_type,
        bl_number=body.bl_number,
        vessel_voyage=body.vessel_voyage,
        container_info=body.container_info,
        load_port=body.load_port,
        discharge_port=body.discharge_port,
        etd=body.etd,
        eta=body.eta,
        status="planned",
        pieces=body.pieces,
        weight_mt=body.weight_mt,
        volume_cbm=body.volume_cbm,
        remarks=body.remarks,
        created_at=now,
        updated_at=now,
    )
    db.add(bl)
    db.commit()
    db.refresh(bl)
    return bl


@router.put("/{order_id}/bls/{bl_id}", response_model=BLOut)
def update_bl(
    order_id: int,
    bl_id: int,
    body: BLUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    order = db.get(FormalOrder, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    if not _can_edit(current_user, order):
        raise HTTPException(status_code=403, detail="权限不足")
    bl = db.get(ShipmentBL, bl_id)
    if not bl or bl.order_id != order_id:
        raise HTTPException(status_code=404, detail="提单不存在")
    for field in ("ship_type", "bl_number", "vessel_voyage", "container_info",
                  "load_port", "discharge_port",
                  "etd", "eta", "status", "pieces", "weight_mt", "volume_cbm", "remarks"):
        val = getattr(body, field)
        if val is not None:
            setattr(bl, field, val)
    bl.updated_at = datetime.utcnow().isoformat()
    db.commit()
    db.refresh(bl)
    return bl


@router.delete("/{order_id}/bls/{bl_id}", status_code=204)
def delete_bl(
    order_id: int,
    bl_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    order = db.get(FormalOrder, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    if not _can_edit(current_user, order):
        raise HTTPException(status_code=403, detail="权限不足")
    bl = db.get(ShipmentBL, bl_id)
    if not bl or bl.order_id != order_id:
        raise HTTPException(status_code=404, detail="提单不存在")
    db.delete(bl)
    db.commit()
