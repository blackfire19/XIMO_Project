import os
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session

from app.core.deps import require_roles
from app.database import get_db
from app.models.accounting import AccountingRecord
from app.models.inquiry import FormalOrder
from app.models.user import User
from app.config import settings

router = APIRouter(prefix="/accounting", tags=["财务记账"])

ALLOWED_UPLOAD_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".xlsx", ".xls", ".docx", ".doc"}


def _now() -> str:
    return datetime.now(timezone.utc).replace(tzinfo=None).isoformat()


def _to_out(rec: AccountingRecord) -> dict:
    return {
        "id": rec.id,
        "order_id": rec.order_id,
        "so_number": rec.order.so_number if rec.order else "",
        "profit": float(rec.profit) if rec.profit is not None else None,
        "notes": rec.notes,
        "salary_calculated": rec.salary_calculated,
        "file_name": rec.file_name,
        "file_path": rec.file_path,
        "recorded_by": rec.recorded_by,
        "recorder_name": rec.recorder.full_name if rec.recorder else "",
        "recorded_at": str(rec.recorded_at),
        "updated_at": str(rec.updated_at),
    }


@router.get("/{order_id}")
def get_record(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("finance")),
):
    rec = db.query(AccountingRecord).filter(AccountingRecord.order_id == order_id).first()
    if not rec:
        raise HTTPException(status_code=404, detail="该订单暂无记账记录")
    return _to_out(rec)


@router.post("/{order_id}")
async def create_or_update_record(
    order_id: int,
    profit: Optional[float] = Form(None),
    notes: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("finance")),
):
    order = db.get(FormalOrder, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    if order.status != "completed":
        raise HTTPException(status_code=400, detail="只能对已完结的订单进行记账")

    rec = db.query(AccountingRecord).filter(AccountingRecord.order_id == order_id).first()
    if rec and rec.salary_calculated:
        raise HTTPException(status_code=400, detail="工资已核算，无法修改记账记录")
    now = _now()

    saved_file_name = None
    saved_file_path = None
    if file and file.filename:
        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in ALLOWED_UPLOAD_EXTENSIONS:
            raise HTTPException(status_code=400, detail="不允许的文件类型，请上传 PDF、图片或 Office 文档")
        upload_dir = os.path.join(settings.UPLOAD_DIR, "accounting", str(order_id))
        os.makedirs(upload_dir, exist_ok=True)
        saved_name = f"{uuid.uuid4().hex}{ext}"
        full_path = os.path.join(upload_dir, saved_name)
        content = await file.read()
        with open(full_path, "wb") as fp:
            fp.write(content)
        saved_file_name = file.filename
        saved_file_path = f"accounting/{order_id}/{saved_name}"

    if rec:
        rec.profit = profit
        rec.notes = notes
        if saved_file_path:
            if rec.file_path:
                old = os.path.join(settings.UPLOAD_DIR, rec.file_path)
                if os.path.exists(old):
                    os.remove(old)
            rec.file_name = saved_file_name
            rec.file_path = saved_file_path
        rec.updated_at = now
    else:
        rec = AccountingRecord(
            order_id=order_id,
            profit=profit,
            notes=notes,
            salary_calculated=False,
            file_name=saved_file_name,
            file_path=saved_file_path,
            recorded_by=current_user.id,
            recorded_at=now,
            updated_at=now,
        )
        db.add(rec)

    db.commit()
    db.refresh(rec)
    return _to_out(rec)


@router.patch("/{order_id}/salary")
def mark_salary(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("finance")),
):
    rec = db.query(AccountingRecord).filter(AccountingRecord.order_id == order_id).first()
    if not rec:
        raise HTTPException(status_code=404, detail="请先创建记账记录")
    if rec.salary_calculated:
        raise HTTPException(status_code=400, detail="工资已核算，无法撤销")
    rec.salary_calculated = True
    rec.updated_at = _now()
    db.commit()
    db.refresh(rec)
    return _to_out(rec)


@router.delete("/{order_id}/file", status_code=204)
def delete_file(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("finance")),
):
    rec = db.query(AccountingRecord).filter(AccountingRecord.order_id == order_id).first()
    if not rec or not rec.file_path:
        raise HTTPException(status_code=404, detail="无附件可删除")
    full_path = os.path.join(settings.UPLOAD_DIR, rec.file_path)
    rec.file_name = None
    rec.file_path = None
    rec.updated_at = _now()
    db.commit()
    if os.path.exists(full_path):
        os.remove(full_path)
