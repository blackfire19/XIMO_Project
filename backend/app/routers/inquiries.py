import os
import uuid
from datetime import datetime, date, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.inquiry import Inquiry, InquiryFile, FormalOrder
from app.models.user import User
from app.schemas.inquiry import (
    InquiryCreate,
    InquiryUpdate,
    InquiryDepositUpdate,
    InquiryListItem,
    InquiryPage,
    InquiryOut,
    InquiryFileOut,
)
from app.config import settings

router = APIRouter(prefix="/inquiries", tags=["询价单"])

INQUIRY_DOC_TYPES = {"pricing_sheet", "pi", "freight_quote"}


# ── 权限 ───────────────────────────────────────────────────
def _can_access(user: User, inq: Inquiry) -> bool:
    role = user.role.name
    if role in ("super_admin", "boss"):
        return True
    if role == "salesperson":
        return inq.salesperson_id == user.id
    return False


def _can_edit(user: User, inq: Inquiry) -> bool:
    role = user.role.name
    if role == "super_admin":
        return True
    if role == "salesperson":
        return inq.salesperson_id == user.id
    return False


# ── 编号生成 ENQ-XIMO{code}YYYYMMDD-01 ────────────────────────
def _gen_enq_number(db: Session, salesperson: User) -> str:
    code = salesperson.salesperson_code or "XX"
    today = datetime.now().strftime("%Y%m%d")
    prefix = f"ENQ-XIMO{code}{today}-"
    used = {
        int(r[0].split("-")[-1])
        for r in db.query(Inquiry.enq_number).filter(Inquiry.enq_number.like(f"{prefix}%")).all()
    }
    seq = 1
    while seq in used:
        seq += 1
    return f"{prefix}{seq:02d}"


# ── 询价单 CRUD ───────────────────────────────────────────────
@router.get("/", response_model=InquiryPage)
def list_inquiries(
    customer_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    enq_number: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(Inquiry)
    if current_user.role.name == "salesperson":
        q = q.filter(Inquiry.salesperson_id == current_user.id)
    if customer_id:
        q = q.filter(Inquiry.customer_id == customer_id)
    if status:
        q = q.filter(Inquiry.status == status)
    if enq_number:
        q = q.filter(Inquiry.enq_number.ilike(f"%{enq_number}%"))
    total = q.count()
    items = (
        q.order_by(Inquiry.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return InquiryPage(total=total, page=page, page_size=page_size, items=items)


@router.post("/", response_model=InquiryOut)
def create_inquiry(
    body: InquiryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role.name == "boss":
        raise HTTPException(status_code=403, detail="老板角色无法创建询价单")

    # 业务员归属：默认当前用户；super_admin 可指定
    salesperson_id = current_user.id
    if body.salesperson_id and current_user.role.name == "super_admin":
        salesperson_id = body.salesperson_id
    salesperson = db.get(User, salesperson_id)
    if not salesperson:
        raise HTTPException(status_code=404, detail="业务员不存在")

    now = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
    for _attempt in range(5):
        inq = Inquiry(
            enq_number=_gen_enq_number(db, salesperson),
            customer_id=body.customer_id,
            salesperson_id=salesperson_id,
            status="active",
            remarks=body.remarks,
            created_by=current_user.id,
            created_at=now,
            updated_at=now,
        )
        db.add(inq)
        try:
            db.flush()
            break
        except IntegrityError:
            db.rollback()
    else:
        raise HTTPException(status_code=500, detail="ENQ 编号生成冲突，请重试")

    db.commit()
    db.refresh(inq)
    return inq


@router.get("/{inquiry_id}", response_model=InquiryOut)
def get_inquiry(
    inquiry_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    inq = db.get(Inquiry, inquiry_id)
    if not inq:
        raise HTTPException(status_code=404, detail="询价单不存在")
    if not _can_access(current_user, inq):
        raise HTTPException(status_code=403, detail="权限不足")
    return inq


@router.put("/{inquiry_id}", response_model=InquiryOut)
def update_inquiry(
    inquiry_id: int,
    body: InquiryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    inq = db.get(Inquiry, inquiry_id)
    if not inq:
        raise HTTPException(status_code=404, detail="询价单不存在")
    if not _can_edit(current_user, inq):
        raise HTTPException(status_code=403, detail="权限不足")
    if body.remarks is not None:
        inq.remarks = body.remarks
    inq.updated_at = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
    db.commit()
    db.refresh(inq)
    return inq


@router.patch("/{inquiry_id}/deposit", response_model=InquiryOut)
def set_deposit(
    inquiry_id: int,
    body: InquiryDepositUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """登记定金 → 状态转为 deposit_received（可转正式订单）"""
    inq = db.get(Inquiry, inquiry_id)
    if not inq:
        raise HTTPException(status_code=404, detail="询价单不存在")
    if not _can_edit(current_user, inq):
        raise HTTPException(status_code=403, detail="权限不足")
    if inq.status == "void":
        raise HTTPException(status_code=400, detail="已失效的询价单无法登记定金")
    if inq.status == "converted":
        raise HTTPException(status_code=400, detail="已转订单的询价单无法修改定金")

    # 必须已上传核价单和 PI 的当前版本，才能登记定金
    current_types = {
        f.doc_type
        for f in db.query(InquiryFile)
        .filter(InquiryFile.inquiry_id == inquiry_id, InquiryFile.is_current.is_(True))
        .all()
    }
    missing = [
        label
        for dt, label in (("pricing_sheet", "核价单"), ("pi", "PI"))
        if dt not in current_types
    ]
    if missing:
        raise HTTPException(status_code=400, detail=f"请先上传：{'、'.join(missing)}")

    inq.deposit_amount = body.deposit_amount
    inq.deposit_date = body.deposit_date or date.today()
    inq.status = "deposit_received"
    inq.updated_at = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
    db.commit()
    db.refresh(inq)
    return inq


@router.patch("/{inquiry_id}/void", response_model=InquiryOut)
def void_inquiry(
    inquiry_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    inq = db.get(Inquiry, inquiry_id)
    if not inq:
        raise HTTPException(status_code=404, detail="询价单不存在")
    if not _can_edit(current_user, inq):
        raise HTTPException(status_code=403, detail="权限不足")
    if inq.status == "converted":
        raise HTTPException(status_code=400, detail="已转订单的询价单无法作废")
    inq.status = "void"
    inq.updated_at = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
    db.commit()
    db.refresh(inq)
    return inq


# ── 文件（多版本归档）────────────────────────────────────────
@router.post("/{inquiry_id}/files", response_model=InquiryFileOut)
async def upload_inquiry_file(
    inquiry_id: int,
    doc_type: str = Form(...),
    note: Optional[str] = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """上传文件：同 doc_type 旧版本自动置为非当前，新版本 is_current=True，保留工作记录"""
    if doc_type not in INQUIRY_DOC_TYPES:
        raise HTTPException(status_code=400, detail=f"doc_type 必须是 {', '.join(INQUIRY_DOC_TYPES)} 之一")
    inq = db.get(Inquiry, inquiry_id)
    if not inq:
        raise HTTPException(status_code=404, detail="询价单不存在")
    if not _can_edit(current_user, inq):
        raise HTTPException(status_code=403, detail="权限不足")

    # 旧版本置为非当前，并计算新版本号
    existing = (
        db.query(InquiryFile)
        .filter(InquiryFile.inquiry_id == inquiry_id, InquiryFile.doc_type == doc_type)
        .all()
    )
    next_version = max((f.version for f in existing), default=0) + 1
    for f in existing:
        f.is_current = False

    upload_dir = os.path.join(settings.UPLOAD_DIR, "inquiry_files", str(inquiry_id))
    os.makedirs(upload_dir, exist_ok=True)
    original_name = file.filename or "file"
    ext = os.path.splitext(original_name)[1]
    saved_name = f"{uuid.uuid4().hex}{ext}"
    saved_path = os.path.join(upload_dir, saved_name)
    content = await file.read()
    with open(saved_path, "wb") as fp:
        fp.write(content)

    rel_path = f"inquiry_files/{inquiry_id}/{saved_name}"
    rec = InquiryFile(
        inquiry_id=inquiry_id,
        doc_type=doc_type,
        version=next_version,
        is_current=True,
        file_name=original_name,
        file_path=rel_path,
        note=note,
        uploaded_by=current_user.id,
        uploaded_at=datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return rec


@router.delete("/{inquiry_id}/files/{file_id}", status_code=204)
def delete_inquiry_file(
    inquiry_id: int,
    file_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    inq = db.get(Inquiry, inquiry_id)
    if not inq:
        raise HTTPException(status_code=404, detail="询价单不存在")
    if not _can_edit(current_user, inq):
        raise HTTPException(status_code=403, detail="权限不足")
    rec = db.get(InquiryFile, file_id)
    if not rec or rec.inquiry_id != inquiry_id:
        raise HTTPException(status_code=404, detail="文件不存在")

    full_path = os.path.join(settings.UPLOAD_DIR, rec.file_path)
    if os.path.exists(full_path):
        os.remove(full_path)
    was_current = rec.is_current
    doc_type = rec.doc_type
    db.delete(rec)
    db.flush()
    # 若删的是当前版本，将同类型最新版本重新设为当前
    if was_current:
        latest = (
            db.query(InquiryFile)
            .filter(InquiryFile.inquiry_id == inquiry_id, InquiryFile.doc_type == doc_type)
            .order_by(InquiryFile.version.desc())
            .first()
        )
        if latest:
            latest.is_current = True
    db.commit()
