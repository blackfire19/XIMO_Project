import os
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from sqlalchemy import func as sqlfunc
from app.core.deps import get_current_user
from app.database import get_db
from app.models.accounting import AccountingRecord
from app.models.inquiry import (
    Inquiry, FormalOrder, OrderFile, ShipmentBL, ShipmentContainer,
)
from app.models.user import User
from app.schemas.inquiry import (
    FormalOrderCreate,
    FormalOrderUpdate,
    FormalOrderStatusUpdate,
    FormalOrderListItem,
    FormalOrderPage,
    FormalOrderOut,
    OrderFileOut,
    BLCreate,
    BLUpdate,
    BLOut,
)
from app.config import settings

router = APIRouter(prefix="/formal-orders", tags=["正式订单"])

# 财务 / 后勤单据：独立于业务员归档，财务后勤可自行上传，且不受出运/工资核算锁定
FINANCE_LOGISTICS_DOC_TYPES = {"fin_ci", "fin_mtc", "fin_pl", "customs_declaration"}
ORDER_DOC_TYPES = {"mtc", "pl", "ci", "co", "export_permit", "inspection", "packing", "ocean_bl", "supplement"} | FINANCE_LOGISTICS_DOC_TYPES
ALLOWED_UPLOAD_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".xlsx", ".xls", ".docx", ".doc"}

# 补充附件：不受出运锁定限制，任何状态均可上传/删除
SUPPLEMENT_DOC_TYPE = "supplement"
# CO 原产地证 / 出口许可证：后勤单据，通常出运阶段或出运后才出具，
# 由后勤+超管维护，完全不受出运/工资核算锁定（出运中、已完结仍可补传/替换）
LOGISTICS_MANAGED_DOC_TYPES = {"co", "export_permit"}
# 进入这些状态后，正式归档文件只读（仅可查看），不能再上传/删除
FILE_LOCK_STATUSES = {"shipping", "completed"}
# 出运阶段例外：海运提单通常出运后才出具，故 shipping 状态仍允许上传/删除
SHIPPING_STAGE_DOC_TYPES = {"ocean_bl"}


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
    if role in ("super_admin", "boss", "finance", "logistics"):
        return True
    if role == "salesperson":
        return order.salesperson_id == user.id
    return False


def _salary_calculated(order: FormalOrder) -> bool:
    rec = order.accounting_record
    return bool(rec and rec.salary_calculated)


def _can_edit(user: User, order: FormalOrder) -> bool:
    if _salary_calculated(order):
        return False   # 工资已核算，全员锁定
    role = user.role.name
    if role == "super_admin":
        return order.status != "completed"
    if role == "salesperson":
        return order.salesperson_id == user.id and order.status != "completed"
    return False


def _can_manage_fin_doc(user: User, order: FormalOrder) -> bool:
    """财务 / 后勤单据：由业务员上传维护（财务、后勤仅下载查看），不受出运/工资核算锁定"""
    role = user.role.name
    if role == "super_admin":
        return True
    if role == "salesperson":
        return order.salesperson_id == user.id
    return False


# 后勤可在订单详情页查看/管理的单据范围（严格受限）
LOGISTICS_VISIBLE_DOC_TYPES = {"fin_ci", "fin_mtc", "fin_pl", "export_permit", "co"}


def _can_manage_logistics_doc(user: User, order: FormalOrder) -> bool:
    """CO 原产地证 / 出口许可证：后勤单据，由后勤+超管维护，不受出运/工资核算锁定。
    这两类单据通常在出运阶段或出运后才出具，故出运中/已完结仍可补传或替换。"""
    return user.role.name in ("super_admin", "logistics")


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
    subject = (body.subject or "").strip()
    if not subject:
        raise HTTPException(status_code=400, detail="请填写订单主题")
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

    now = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
    for _attempt in range(5):
        order = FormalOrder(
            so_number=_gen_so_number(db, salesperson),
            inquiry_id=inq.id,
            customer_id=inq.customer_id,
            salesperson_id=inq.salesperson_id,
            is_stock=body.is_stock,
            est_production_date=body.est_production_date,
            subject=subject,
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


@router.get("/", response_model=FormalOrderPage)
def list_orders(
    customer_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    so_number: Optional[str] = Query(None),
    active: bool = Query(False),
    salesperson_id: Optional[int] = Query(None),
    has_accounting: Optional[bool] = Query(None),
    salary_calculated: Optional[bool] = Query(None),
    upload_status: Optional[str] = Query(None),  # 后勤：all/partial/none（出口许可证+CO）
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(FormalOrder)
    # 后勤：只读跟单，禁止通过财务筛选参数推断记账/工资状态
    if current_user.role.name == "logistics":
        has_accounting = None
        salary_calculated = None
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
    # 财务专用筛选
    if salesperson_id:
        q = q.filter(FormalOrder.salesperson_id == salesperson_id)
    if has_accounting is not None:
        accounted_ids = db.query(AccountingRecord.order_id)
        if has_accounting:
            q = q.filter(FormalOrder.id.in_(accounted_ids))
        else:
            q = q.filter(FormalOrder.id.notin_(accounted_ids))
    if salary_calculated is not None:
        q = q.outerjoin(AccountingRecord, AccountingRecord.order_id == FormalOrder.id)
        if salary_calculated:
            q = q.filter(AccountingRecord.salary_calculated == True)
        else:
            q = q.filter(
                (AccountingRecord.id == None) | (AccountingRecord.salary_calculated == False)
            )
    # 后勤上传状态筛选：基于出口许可证(export_permit) + CO(co) 是否齐全
    if upload_status in ("all", "partial", "none"):
        co_ids = db.query(OrderFile.order_id).filter(OrderFile.doc_type == "co")
        ep_ids = db.query(OrderFile.order_id).filter(OrderFile.doc_type == "export_permit")
        if upload_status == "all":
            q = q.filter(FormalOrder.id.in_(co_ids), FormalOrder.id.in_(ep_ids))
        elif upload_status == "none":
            q = q.filter(FormalOrder.id.notin_(co_ids), FormalOrder.id.notin_(ep_ids))
        else:  # partial：恰好缺其中之一
            q = q.filter(
                ((FormalOrder.id.in_(co_ids)) & (FormalOrder.id.notin_(ep_ids)))
                | ((FormalOrder.id.notin_(co_ids)) & (FormalOrder.id.in_(ep_ids)))
            )
    total = q.count()
    # 全量利润合计（所有筛选条件下，跨所有分页）
    profit_total_row = (
        db.query(sqlfunc.sum(AccountingRecord.profit))
        .filter(AccountingRecord.order_id.in_(q.with_entities(FormalOrder.id)))
        .scalar()
    )
    profit_total = float(profit_total_row) if profit_total_row is not None else None
    items = (
        q.order_by(FormalOrder.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    # 后勤：只读跟单，屏蔽利润/工资等财务数据
    item_out = [FormalOrderListItem.model_validate(o) for o in items]
    if current_user.role.name == "logistics":
        for it in item_out:
            it.profit = None
            it.salary_calculated = None
        profit_total = None
    # 后勤/超管视角：计算出口单据上传状态（export_permit + co）
    if current_user.role.name in ("logistics", "super_admin"):
        item_ids = [o.id for o in items]
        have_map: dict[int, set[str]] = {}
        if item_ids:
            rows = (
                db.query(OrderFile.order_id, OrderFile.doc_type)
                .filter(
                    OrderFile.order_id.in_(item_ids),
                    OrderFile.doc_type.in_(["co", "export_permit"]),
                )
                .distinct()
                .all()
            )
            for oid, dt in rows:
                have_map.setdefault(oid, set()).add(dt)
        for it in item_out:
            have = have_map.get(it.id, set())
            has_co = "co" in have
            has_ep = "export_permit" in have
            missing = []
            if not has_ep:
                missing.append("export_permit")
            if not has_co:
                missing.append("co")
            it.missing_docs = missing
            if not missing:
                it.upload_status = "all"
            elif has_co or has_ep:
                it.upload_status = "partial"
            else:
                it.upload_status = "none"
    return FormalOrderPage(total=total, page=page, page_size=page_size, items=item_out, profit_total=profit_total)


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
    out = FormalOrderOut.model_validate(order)
    if current_user.role.name == "logistics":
        out.profit = None
        out.salary_calculated = None
        # 后勤严格受限：仅查看 fin CI/MTC、出口许可证、CO，其余单据（询价单文件、归档、报关单、补充附件）全部隐藏
        out.inquiry_files = []
        out.files = [f for f in out.files if f.doc_type in LOGISTICS_VISIBLE_DOC_TYPES]
    return out


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
    for field in ("is_stock", "est_production_date", "subject", "remarks"):
        val = getattr(body, field)
        if val is not None:
            setattr(order, field, val)
    order.updated_at = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
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
    order.updated_at = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
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
    if doc_type in LOGISTICS_MANAGED_DOC_TYPES:
        # CO / 出口许可证：后勤单据，后勤+超管维护，不受出运/工资核算锁定
        if not _can_manage_logistics_doc(current_user, order):
            raise HTTPException(status_code=403, detail="权限不足")
    elif doc_type in FINANCE_LOGISTICS_DOC_TYPES:
        # 财务 / 后勤单据：独立权限，不受出运/工资核算锁定
        if not _can_manage_fin_doc(current_user, order):
            raise HTTPException(status_code=403, detail="权限不足")
    else:
        salary_locked = _salary_calculated(order)
        if salary_locked:
            if current_user.role.name == "finance":
                raise HTTPException(status_code=403, detail="工资已核算，财务无法修改此订单")
            if not _can_edit(current_user, order) and doc_type == SUPPLEMENT_DOC_TYPE:
                raise HTTPException(status_code=403, detail="权限不足")
            if doc_type != SUPPLEMENT_DOC_TYPE:
                raise HTTPException(status_code=400, detail="工资已核算，仅可上传补充附件")
        else:
            if not _can_edit(current_user, order):
                raise HTTPException(status_code=403, detail="权限不足")
        shipping_stage_exception = order.status == "shipping" and doc_type in SHIPPING_STAGE_DOC_TYPES
        if doc_type != SUPPLEMENT_DOC_TYPE and order.status in FILE_LOCK_STATUSES and not shipping_stage_exception:
            raise HTTPException(status_code=400, detail="订单已进入出运阶段，归档文件已锁定，仅可上传补充附件")

    original_name = file.filename or "file"
    ext = os.path.splitext(original_name)[1].lower()
    if ext not in ALLOWED_UPLOAD_EXTENSIONS:
        raise HTTPException(status_code=400, detail="不允许的文件类型，请上传 PDF、图片或 Office 文档")

    upload_dir = os.path.join(settings.UPLOAD_DIR, "order_files", str(order_id))
    os.makedirs(upload_dir, exist_ok=True)
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
        uploaded_at=datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
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
    rec = db.get(OrderFile, file_id)
    if not rec or rec.order_id != order_id:
        raise HTTPException(status_code=404, detail="文件不存在")
    if rec.doc_type in LOGISTICS_MANAGED_DOC_TYPES:
        # CO / 出口许可证：后勤单据，后勤+超管维护，不受出运/工资核算锁定
        if not _can_manage_logistics_doc(current_user, order):
            raise HTTPException(status_code=403, detail="权限不足")
    elif rec.doc_type in FINANCE_LOGISTICS_DOC_TYPES:
        # 财务 / 后勤单据：独立权限，不受出运/工资核算锁定
        if not _can_manage_fin_doc(current_user, order):
            raise HTTPException(status_code=403, detail="权限不足")
    else:
        if _salary_calculated(order):
            raise HTTPException(status_code=403, detail="工资已核算，文件不可删除")
        if not _can_edit(current_user, order):
            raise HTTPException(status_code=403, detail="权限不足")
        if rec.doc_type == SUPPLEMENT_DOC_TYPE:
            raise HTTPException(status_code=400, detail="补充附件上传后不可删除")
        shipping_stage_exception = order.status == "shipping" and rec.doc_type in SHIPPING_STAGE_DOC_TYPES
        if order.status in FILE_LOCK_STATUSES and not shipping_stage_exception:
            raise HTTPException(status_code=400, detail="订单已进入出运阶段，归档文件已锁定")
    full_path = os.path.join(settings.UPLOAD_DIR, rec.file_path)
    db.delete(rec)
    db.commit()
    if os.path.exists(full_path):
        os.remove(full_path)


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

    now = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
    bl = ShipmentBL(
        order_id=order_id,
        ship_type=body.ship_type,
        carrier=body.carrier,
        bl_number=body.bl_number,
        vessel_voyage=body.vessel_voyage,
        container_info=body.container_info,
        load_port=body.load_port,
        discharge_port=body.discharge_port,
        discharge_country=body.discharge_country,
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
    db.flush()  # 获取 bl.id 后再插入集装箱

    for c in body.containers:
        db.add(ShipmentContainer(
            bl_id=bl.id,
            container_type=c.container_type,
            container_number=c.container_number,
            seal_number=c.seal_number,
        ))

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
    for field in ("ship_type", "carrier", "bl_number", "vessel_voyage", "container_info",
                  "load_port", "discharge_port", "discharge_country",
                  "etd", "eta", "status", "pieces", "weight_mt", "volume_cbm", "remarks"):
        val = getattr(body, field)
        if val is not None:
            setattr(bl, field, val)
    bl.updated_at = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
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
